const express = require('express');
const reportController = require('../controllers/reportController');

const router = express.Router();

router.get('/financial-report', reportController.getFinancialReport);

module.exports = router;
