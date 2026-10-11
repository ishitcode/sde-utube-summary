const test = require('node:test');
const assert = require('node:assert/strict');

const { createCacheStore } = require('../src/utils/cache');

test('cache store can clear entries and force refresh behavior', () => {
  const cache = createCacheStore({ ttlMs: 60_000 });
  const key = 'video-123';

  cache.set(key, { quick_summary: 'old summary' });
  assert.equal(cache.get(key)?.quick_summary, 'old summary');

  cache.clear();
  assert.equal(cache.get(key), null);

  const refreshKey = 'video-456';
  cache.set(refreshKey, { quick_summary: 'fresh summary' });
  assert.equal(cache.get(refreshKey)?.quick_summary, 'fresh summary');
  assert.equal(cache.get(refreshKey, true), null);
});
