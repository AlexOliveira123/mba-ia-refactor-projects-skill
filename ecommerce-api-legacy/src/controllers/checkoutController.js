const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const paymentGateway = require('../services/paymentGateway');
const cache = require('../cache');

function parseCheckoutInput(body) {
  return {
    username: body.usr,
    email: body.eml,
    password: body.pwd,
    courseId: body.c_id,
    cardNumber: body.card,
  };
}

function validateCheckoutInput({ username, email, courseId, cardNumber }) {
  if (!username || !email || !courseId || !cardNumber) return 'Bad Request';
  if (!/^\S+@\S+\.\S+$/.test(email)) return 'Bad Request';
  if (!Number.isInteger(Number(courseId))) return 'Bad Request';
  if (!/^\d{13,19}$/.test(String(cardNumber))) return 'Bad Request';
  return null;
}

async function checkout(req, res, next) {
  try {
    const input = parseCheckoutInput(req.body);
    const validationError = validateCheckoutInput(input);
    if (validationError) return res.status(400).send(validationError);

    const course = await courseModel.findActiveById(input.courseId);
    if (!course) return res.status(404).send('Curso não encontrado');

    const existingUser = await userModel.findByEmail(input.email);
    let userId;

    if (!existingUser) {
      if (!input.password) {
        return res.status(400).send('Senha é obrigatória para criar uma conta');
      }
      const hashedPassword = userModel.hashPassword(input.password);
      const { lastID } = await userModel.create({
        name: input.username,
        email: input.email,
        hashedPassword,
      });
      userId = lastID;
    } else {
      userId = existingUser.id;
    }

    const { status } = paymentGateway.charge({ cardNumber: input.cardNumber });
    if (status === 'DENIED') return res.status(400).send('Pagamento recusado');

    const { lastID: enrollmentId } = await enrollmentModel.create({ userId, courseId: input.courseId });
    await paymentModel.create({ enrollmentId, amount: course.price, status });
    await auditLogModel.record(`Checkout curso ${input.courseId} por ${userId}`);

    cache.set(`last_checkout_${userId}`, course.title);

    res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
  } catch (err) {
    next(err);
  }
}

module.exports = { checkout, parseCheckoutInput, validateCheckoutInput };
