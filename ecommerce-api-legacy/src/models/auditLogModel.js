const { dbRun } = require('../database');

function record(action) {
  return dbRun("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
}

module.exports = { record };
