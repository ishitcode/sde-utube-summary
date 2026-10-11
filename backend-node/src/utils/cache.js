function createCacheStore({ ttlMs = 24 * 60 * 60 * 1000 } = {}) {
  const store = new Map();

  const now = () => Date.now();

  function get(key, forceRefresh = false) {
    const entry = store.get(key);
    if (!entry) return null;

    if (forceRefresh) {
      store.delete(key);
      return null;
    }

    if (now() > entry.expiresAt) {
      store.delete(key);
      return null;
    }

    return entry.value;
  }

  function set(key, value) {
    store.set(key, {
      value,
      expiresAt: now() + ttlMs,
    });
    return value;
  }

  function clear() {
    store.clear();
  }

  function has(key) {
    return get(key) !== null;
  }

  return { get, set, clear, has, size: () => store.size };
}

module.exports = { createCacheStore };
