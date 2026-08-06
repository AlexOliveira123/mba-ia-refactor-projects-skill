const crypto = require('crypto');
const { dbGet, dbRun } = require('../database');

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  return `${salt}:${derivedKey.toString('hex')}`;
}

function verifyPassword(password, stored) {
  const [salt, storedHex] = stored.split(':');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  const storedBuffer = Buffer.from(storedHex, 'hex');
  return derivedKey.length === storedBuffer.length && crypto.timingSafeEqual(derivedKey, storedBuffer);
}

function findByEmail(email) {
  return dbGet('SELECT * FROM users WHERE email = ?', [email]);
}

function findById(id) {
  return dbGet('SELECT * FROM users WHERE id = ?', [id]);
}

function create({ name, email, hashedPassword }) {
  return dbRun('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, hashedPassword]);
}

function remove(id) {
  return dbRun('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { hashPassword, verifyPassword, findByEmail, findById, create, remove };
