const { YoutubeTranscript } = require('youtube-transcript');

const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://localhost:8001';

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

function selectSummaryTranscript(transcript, summaryStart, summaryEnd) {
  if (summaryStart === undefined && summaryEnd === undefined) return transcript;
  if (summaryStart === undefined || summaryEnd === undefined) {
    throw new Error('Both summary start and end times are required.');
  }
  if (!Number.isFinite(summaryStart) || !Number.isFinite(summaryEnd) || summaryStart < 0 || summaryEnd <= summaryStart) {
    throw new Error('Summary end time must be greater than a non-negative start time.');
  }

  const selected = transcript.filter((segment) => segment.end > summaryStart && segment.start < summaryEnd);
  if (!selected.length) throw new Error('No transcript is available in the selected time range.');
  return selected;
}

async function generateSummaryFromTranscript(transcript, outputLanguage = 'English', options = {}) {
  const response = await fetch(`${RAG_SERVICE_URL}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      segments: transcript,
      output_language: outputLanguage,
      summary_start: options.summaryStart,
      summary_end: options.summaryEnd,
      request_id: options.requestId,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || `LangGraph summary generation failed (${response.status}).`);
    error.statusCode = response.status;
    throw error;
  }

  return response.json();
}

module.exports = {
  fetchTranscript,
  generateSummaryFromTranscript,
  selectSummaryTranscript,
};
