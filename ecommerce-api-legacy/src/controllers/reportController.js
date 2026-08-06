const reportModel = require('../models/reportModel');

async function getFinancialReport(req, res, next) {
  try {
    const report = await reportModel.getFinancialReport();
    res.json(report);
  } catch (err) {
    next(err);
  }
}

module.exports = { getFinancialReport };
