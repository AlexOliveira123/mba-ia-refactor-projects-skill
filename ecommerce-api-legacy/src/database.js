const sqlite3 = require('sqlite3').verbose();

const db = new sqlite3.Database(':memory:');

function dbGet(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
  });
}

function dbAll(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
  });
}

function dbRun(sql, params = []) {
  return new Promise((resolve, reject) => {
    // A plain `function` expression (not an arrow function) is required here:
    // the sqlite3 driver binds `this.lastID`/`this.changes` on the callback's
    // own `this`, and that binding only happens for non-arrow functions.
    db.run(sql, params, function callback(err) {
      if (err) return reject(err);
      resolve({ lastID: this.lastID, changes: this.changes });
    });
  });
}

function initSchema() {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      // SQLite does not enforce declared FOREIGN KEY constraints unless this
      // pragma is turned on for the connection.
      db.run('PRAGMA foreign_keys = ON');
      db.run('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
      db.run('CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
      // ON DELETE CASCADE is required here, not optional: DELETE /api/users/:id
      // (see routes/userRoutes.js) must keep succeeding exactly as before once
      // foreign_keys enforcement is on. Without CASCADE, deleting a user with
      // existing enrollments/payments would hit a FOREIGN KEY constraint
      // violation and turn a previously-successful (if messy) delete into a
      // request failure — a behavior change this refactoring does not permit.
      db.run(`CREATE TABLE enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        course_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
      )`);
      db.run(`CREATE TABLE payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER,
        amount REAL,
        status TEXT,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
      )`);
      db.run('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)', (err) => {
        if (err) return reject(err);
        resolve();
      });
    });
  });
}

function seed({ seedUserPasswordHash }) {
  return dbRun('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
    'Leonan', 'leonan@fullcycle.com.br', seedUserPasswordHash,
  ])
    .then(() => dbRun("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)"))
    .then(() => dbRun('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)'))
    .then(({ lastID }) => dbRun('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, 997.00, ?)', [lastID, 'PAID']));
}

module.exports = { dbGet, dbAll, dbRun, initSchema, seed };
