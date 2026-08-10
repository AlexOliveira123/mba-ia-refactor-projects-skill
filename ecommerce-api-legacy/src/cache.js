class Cache {
  constructor() {
    this._store = new Map();
  }

  set(key, value) {
    console.log(`[LOG] Salvando no cache: ${key}`);
    this._store.set(key, value);
  }

  get(key) {
    return this._store.get(key);
  }
}

module.exports = new Cache();
