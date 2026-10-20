const test = require('node:test');
const assert = require('node:assert/strict');

const { selectSummaryTranscript } = require('../src/services/llmSummary');

test('selects transcript segments overlapping the requested summary range', () => {
  const transcript = [
    { text: 'opening', start: 0, end: 10 },
    { text: 'middle', start: 10, end: 20 },
    { text: 'closing', start: 20, end: 30 },
  ];

  assert.deepEqual(selectSummaryTranscript(transcript, 9, 21), transcript);
  assert.deepEqual(selectSummaryTranscript(transcript, 10, 20), [transcript[1]]);
  assert.deepEqual(selectSummaryTranscript(transcript), transcript);
});

test('rejects incomplete or invalid summary ranges', () => {
  const transcript = [{ text: 'opening', start: 0, end: 10 }];

  assert.throws(() => selectSummaryTranscript(transcript, 0), /Both summary start and end/);
  assert.throws(() => selectSummaryTranscript(transcript, 10, 5), /greater than/);
  assert.throws(() => selectSummaryTranscript(transcript, 20, 30), /No transcript/);
});
