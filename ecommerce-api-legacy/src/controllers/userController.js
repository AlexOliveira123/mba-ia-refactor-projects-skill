const userModel = require('../models/userModel');

async function remove(req, res, next) {
  try {
    await userModel.remove(req.params.id);
    res.send('Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.');
  } catch (err) {
    next(err);
  }
}

module.exports = { remove };
