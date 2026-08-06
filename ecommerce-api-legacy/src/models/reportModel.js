const { dbAll } = require('../database');

const REPORT_QUERY = `
  SELECT
    c.id     AS course_id,
    c.title  AS course_title,
    e.id     AS enrollment_id,
    u.name   AS student_name,
    p.amount AS payment_amount,
    p.status AS payment_status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u       ON u.id = e.user_id
  LEFT JOIN payments p    ON p.enrollment_id = e.id
  ORDER BY c.id
`;

function groupRowsByCourse(rows) {
  const courseMap = new Map();

  for (const row of rows) {
    if (!courseMap.has(row.course_id)) {
      courseMap.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
    }
    const courseData = courseMap.get(row.course_id);

    if (row.enrollment_id === null) continue; // course with no enrollments yet

    if (row.payment_status === 'PAID' && row.payment_amount !== null) {
      courseData.revenue += row.payment_amount;
    }

    courseData.students.push({
      student: row.student_name !== null ? row.student_name : 'Unknown',
      paid: row.payment_amount !== null ? row.payment_amount : 0,
    });
  }

  return Array.from(courseMap.values());
}

async function getFinancialReport() {
  const rows = await dbAll(REPORT_QUERY);
  return groupRowsByCourse(rows);
}

module.exports = { getFinancialReport, groupRowsByCourse };
