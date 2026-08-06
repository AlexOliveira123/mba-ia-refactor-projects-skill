const { adminToken } = require('../config/settings');

function adminAuth(req, res, next) {
  const token = req.get('X-Admin-Token');
  if (!token || token !== adminToken) {
    return res.status(401).send('Unauthorized');
  }
  next();
}

module.exports = adminAuth;
