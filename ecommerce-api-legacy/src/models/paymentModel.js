const { dbRun } = require('../database');

function create({ enrollmentId, amount, status }) {
  return dbRun('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
}

module.exports = { create };
