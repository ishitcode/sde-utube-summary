const test = require('node:test');
const assert = require('node:assert/strict');

const { parseGeminiSummaryResponse } = require('../src/services/llmSummary');

test('parses Gemini JSON summary response into app summary shape', () => {
  const raw = [
    'Here is the summary:',
    '```json',
    '{',
    '  "quick_summary": "This lecture explains the core idea in a structured way.",',
    '  "detailed_notes": ["A clear note", "A second note"],',
    '  "key_concepts": ["Idea", "Practice"],',
    '  "timestamp_references": [{"start": 0, "end": 20, "label": "Intro"}]',
    '}',
    '```',
    '',
  ].join('\n');

  const parsed = parseGeminiSummaryResponse(raw);
  assert.equal(parsed.quick_summary.includes('core idea'), true);
  assert.deepEqual(parsed.key_concepts, ['Idea', 'Practice']);
  assert.equal(parsed.timestamp_references[0].label, 'Intro');
});
