const { dbRun } = require('../database');

function create({ userId, courseId }) {
  return dbRun('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
}

module.exports = { create };
