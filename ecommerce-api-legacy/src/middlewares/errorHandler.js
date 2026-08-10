function errorHandler(err, req, res, next) {
  console.error('[ERROR]', err);
  res.status(500).send('Erro interno do servidor');
}

module.exports = errorHandler;
