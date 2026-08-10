const express = require('express');
const settings = require('./config/settings');
const database = require('./database');
const userModel = require('./models/userModel');
const checkoutRoutes = require('./routes/checkoutRoutes');
const userRoutes = require('./routes/userRoutes');
const reportRoutes = require('./routes/reportRoutes');
const errorHandler = require('./middlewares/errorHandler');

async function start() {
  const app = express();
  app.use(express.json());

  await database.initSchema();
  await database.seed({ seedUserPasswordHash: userModel.hashPassword('123') });

  app.use('/api/checkout', checkoutRoutes);
  app.use('/api/users', userRoutes);
  app.use('/api/admin', reportRoutes);

  app.use(errorHandler);

  app.listen(settings.port, () => {
    console.log(`Frankenstein LMS rodando na porta ${settings.port}...`);
  });
}

start();

module.exports = { start };
