const express = require('express');
const adminAuth = require('../middlewares/adminAuth');
const userController = require('../controllers/userController');

const router = express.Router();

router.delete('/:id', adminAuth, userController.remove);

module.exports = router;
