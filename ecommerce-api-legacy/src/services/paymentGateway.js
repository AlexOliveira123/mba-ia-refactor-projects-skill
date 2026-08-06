const VISA_PREFIX = '4';

/**
 * Mock payment approval. This is NOT a real payment-gateway integration —
 * the original project never called an external processor, and adding one
 * is out of scope for this refactoring. This module exists to isolate the
 * mock decision behind one named, documented boundary instead of leaving it
 * inline inside a route handler, so a real integration can later replace
 * only this file without touching any controller or model.
 */
function charge({ cardNumber }) {
  const status = cardNumber.startsWith(VISA_PREFIX) ? 'PAID' : 'DENIED';
  return { status };
}

module.exports = { charge, VISA_PREFIX };
