const { YoutubeTranscript } = require('youtube-transcript');

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-3.8-flash';

function normalizeTranscriptSegments(transcript, preferredLanguage = 'auto') {
  return transcript.map((item, index) => ({
    text: String(item.text || '').trim(),
    start: Number(item.start || 0),
    end: Number((item.start || 0) + (item.duration || 0)),
    language: preferredLanguage && preferredLanguage.toLowerCase() !== 'auto' ? preferredLanguage : (item.language || 'en'),
    source: 'youtube-transcript',
    index,
  })).filter((segment) => segment.text);
}

async function fetchTranscript(videoId, preferredLanguage = 'auto') {
  try {
    const config = preferredLanguage && preferredLanguage.toLowerCase() !== 'auto' ? { lang: preferredLanguage } : undefined;
    const transcript = await YoutubeTranscript.fetchTranscript(videoId, config);
    return normalizeTranscriptSegments(transcript, preferredLanguage);
  } catch (error) {
    throw new Error(`Could not fetch transcript for video ${videoId}: ${error.message}`);
  }
}

function parseGeminiSummaryResponse(rawText) {
  const text = String(rawText || '').trim();
  if (!text) {
    throw new Error('Empty response from Gemini summary model.');
  }

  const fencedMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  const candidate = fencedMatch ? fencedMatch[1] : text;
  const jsonText = candidate.trim();
  const parsed = JSON.parse(jsonText);

  return {
    quick_summary: String(parsed.quick_summary || 'This lecture was summarized successfully from the transcript.').trim(),
    detailed_notes: Array.isArray(parsed.detailed_notes) ? parsed.detailed_notes.map((item) => String(item)) : [],
    key_concepts: Array.isArray(parsed.key_concepts) ? parsed.key_concepts.map((item) => String(item)) : [],
    timestamp_references: Array.isArray(parsed.timestamp_references)
      ? parsed.timestamp_references.map((entry) => ({
          start: Number(entry.start || 0),
          end: Number(entry.end || 0),
          label: String(entry.label || 'Key segment'),
        }))
      : [],
  };
}

async function generateSummaryFromTranscript(transcript, outputLanguage = 'English') {
  if (!GEMINI_API_KEY) {
    return {
      quick_summary: 'Transcript fetched successfully. Add GEMINI_API_KEY to generate a model-based summary.',
      detailed_notes: [
        'The lecture transcript was retrieved and is ready for AI summarization.',
        'Set GEMINI_API_KEY to enable live LLM summarization.',
      ],
      key_concepts: ['Transcript loaded', 'LLM summary pending', 'Study notes ready'],
      timestamp_references: transcript.slice(0, 3).map((segment) => ({
        start: segment.start,
        end: segment.end,
        label: 'Lecture segment',
      })),
    };
  }

  const transcriptText = transcript
    .map((segment, index) => `[${index}] ${segment.start}s - ${segment.text}`)
    .join('\n');

  const prompt = `You are an expert tutor and educator. Summarize the transcript below for a student studying the lecture.

Return ONLY valid JSON with this exact structure:
{
  "quick_summary": "string",
  "detailed_notes": ["string", "string"],
  "key_concepts": ["string", "string"],
  "timestamp_references": [{"start": number, "end": number, "label": "string"}]
}

Requirements:
- Keep the summary concise and study-friendly.
- Write in ${outputLanguage}.
- Use accurate facts only from the transcript.
- Include 2-4 detailed notes.
- Include 3-6 key concepts.
- Keep transcript timestamps aligned to the actual lecture.

Transcript:
${transcriptText}`;

  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.2,
        topP: 0.8,
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Gemini summary generation failed (${response.status}): ${text.slice(0, 400)}`);
  }

  const payload = await response.json();
  const rawSummary = payload?.candidates?.[0]?.content?.parts
    ?.map((part) => part.text)
    .join('\n') || '';

  return parseGeminiSummaryResponse(rawSummary);
}

module.exports = {
  fetchTranscript,
  generateSummaryFromTranscript,
  parseGeminiSummaryResponse,
};
