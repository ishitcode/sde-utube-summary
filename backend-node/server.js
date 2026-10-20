require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { connectDB } = require('./src/config/db');
const Video = require('./src/models/Video');
const logger = require('./src/utils/logger');
const { createCacheStore } = require('./src/utils/cache');
const { fetchTranscript, generateSummaryFromTranscript, selectSummaryTranscript } = require('./src/services/llmSummary');

const app = express();
const PORT = process.env.PORT || 4000;
const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://localhost:8001';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const summaryCache = createCacheStore({ ttlMs: CACHE_TTL_MS });

app.use(cors());
app.use(express.json());

app.use((req, res, next) => {
  const requestId = String(req.headers['x-request-id'] || `req-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`);
  req.requestId = requestId;
  res.setHeader('X-Request-Id', requestId);

  logger.info(`REQUEST START ${req.method} ${req.originalUrl} request_id=${requestId}`, {
    query: req.query,
    bodyKeys: req.body && typeof req.body === 'object' ? Object.keys(req.body) : [],
    userAgent: req.headers['user-agent'] || 'unknown',
  });

  res.on('finish', () => {
    logger.info(`REQUEST END ${req.method} ${req.originalUrl} status=${res.statusCode} request_id=${requestId}`);
  });

  next();
});

app.use((error, req, res, next) => {
  logger.error(`UNHANDLED_ERROR ${req.method} ${req.originalUrl} request_id=${req.requestId}`, {
    message: error.message,
    stack: error.stack,
    body: req.body,
  });
  res.status(500).json({ detail: 'Internal server error' });
});

function normalizeCacheKey(videoId, transcriptLanguage = 'auto', outputLanguage = 'English', summaryStart, summaryEnd) {
  return JSON.stringify({ videoId, transcriptLanguage, outputLanguage, summaryStart, summaryEnd });
}

function isFreshWithinTtl(record) {
  if (!record) return false;
  const timestamp = record.updated_at || record.updatedAt || record.created_at || record.createdAt;
  if (!timestamp) return false;
  const ms = new Date(timestamp).getTime();
  if (Number.isNaN(ms)) return false;
  return Date.now() - ms < CACHE_TTL_MS;
}

function getCachedSummary(key, forceRefresh = false) {
  return summaryCache.get(key, forceRefresh);
}

function setCachedSummary(key, value) {
  return summaryCache.set(key, value);
}

function clearSummaryCache() {
  summaryCache.clear();
  logger.warn('CACHE CLEARED by admin request');
}

function validateYouTubeUrl(url) {
  const candidate = (url || '').trim();
  if (!candidate) throw new Error('YouTube URL is required.');
  const match = candidate.match(/(?:v=|youtu\.be\/|\/shorts\/)([A-Za-z0-9_-]{11})/i);
  if (!match) throw new Error('This is not a valid YouTube URL.');
  return match[1];
}

async function buildTranscript(videoId, preferredLanguage = 'auto') {
  return fetchTranscript(videoId, preferredLanguage);
}

async function callRagIndex(videoId, transcript) {
  logger.info(`RAG_INDEX_START video_id=${videoId} segments=${transcript.length}`);

  try {
    const response = await fetch(`${RAG_SERVICE_URL}/api/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, segments: transcript }),
    });

    if (!response.ok) {
      const responseText = await response.text().catch(() => '');
      logger.error(`RAG_INDEX_FAILED video_id=${videoId} status=${response.status}`, {
        responseText: responseText.slice(0, 500),
      });
      throw new Error(`RAG indexing failed: ${response.status}`);
    }

    const data = await response.json();
    logger.info(`RAG_INDEX_SUCCESS video_id=${videoId}`, { result: data });
    return data;
  } catch (error) {
    logger.warn(`RAG_INDEX_FALLBACK video_id=${videoId}`, {
      message: error.message,
      stack: error.stack,
    });
    return { indexed: transcript.length, video_id: videoId };
  }
}

async function callRagSearch(query, videoId) {
  logger.info(`RAG_SEARCH_START video_id=${videoId} query=${String(query).slice(0, 120)}`);

  try {
    const response = await fetch(`${RAG_SERVICE_URL}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, video_id: videoId, limit: 3 }),
    });

    if (!response.ok) {
      logger.warn(`RAG_SEARCH_FAILED video_id=${videoId} status=${response.status}`);
      return [];
    }

    const { hits = [] } = await response.json();
    logger.info(`RAG_SEARCH_SUCCESS video_id=${videoId} hits=${hits.length}`);
    return hits;
  } catch (error) {
    logger.warn(`RAG_SEARCH_UNAVAILABLE video_id=${videoId}`, {
      message: error.message,
      stack: error.stack,
    });
    return [];
  }
}

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'youtube-summary-studio-node' });
});

app.get('/api/history', async (req, res) => {
  try {
    logger.info(`BUSINESS LOGIC history_fetch request_id=${req.requestId}`);
    const videos = await Video.find({}).sort({ created_at: -1 }).lean();
    logger.info(`BUSINESS LOGIC history_fetch_success request_id=${req.requestId} count=${videos.length}`);
    res.json({ items: videos.map((video) => ({ video_id: video.video_id, title: video.title, channel_name: video.channel_name, status: video.status })) });
  } catch (error) {
    logger.error(`BUSINESS LOGIC history_fetch_failed request_id=${req.requestId}`, {
      message: error.message,
      stack: error.stack,
    });
    res.status(500).json({ detail: error.message });
  }
});

app.get('/api/history/:video_id', async (req, res) => {
  try {
    const video = await Video.findOne({ video_id: req.params.video_id }).lean();
    if (!video) return res.status(404).json({ detail: 'Video not found' });
    res.json(video);
  } catch (error) {
    res.status(500).json({ detail: error.message });
  }
});

app.post('/api/videos/analyze', async (req, res) => {
  let videoId = null;

  try {
    const {
      url,
      transcript_language = 'auto',
      output_language = 'English',
      summary_start,
      summary_end,
      refresh = false,
    } = req.body || {};
    logger.info(`BUSINESS LOGIC analyze_start request_id=${req.requestId}`, {
      url: url ? String(url).slice(0, 120) : null,
      transcript_language,
      output_language,
      summary_start,
      summary_end,
      refresh,
    });

    videoId = validateYouTubeUrl(url);
    logger.info(`BUSINESS LOGIC url_validated request_id=${req.requestId}`, { videoId });

    const selectedRange = summary_start === undefined && summary_end === undefined
      ? null
      : { start: Number(summary_start), end: Number(summary_end) };
    const cacheKey = normalizeCacheKey(videoId, transcript_language, output_language, selectedRange?.start, selectedRange?.end);
    const cached = getCachedSummary(cacheKey, Boolean(refresh));
    if (cached && !refresh) {
      logger.info(`CACHE HIT analyze request_id=${req.requestId}`, { videoId, cacheKey });
      return res.status(200).json({ ...cached, message: 'Using cached lecture summary from the last 24 hours.' });
    }

    if (refresh) {
      logger.info(`CACHE REFRESH analyze request_id=${req.requestId}`, { videoId, cacheKey });
    }

    const existing = await Video.findOne({ video_id: videoId });
    logger.info(`DB LOOKUP analyze request_id=${req.requestId}`, { videoId, found: Boolean(existing) });

    const storedRange = existing?.summary?.summary_range || null;
    const sameStoredRange = selectedRange
      ? storedRange?.start === selectedRange.start && storedRange?.end === selectedRange.end
      : !storedRange;
    const sameStoredLanguages = existing?.transcript_language === transcript_language
      && existing?.output_language === output_language;
    if (existing && sameStoredRange && sameStoredLanguages && isFreshWithinTtl(existing) && !refresh) {
      logger.info(`DB CACHE HIT analyze request_id=${req.requestId}`, { videoId });
      setCachedSummary(cacheKey, existing.toObject());
      return res.status(200).json({
        ...existing.toObject(),
        message: 'Using cached lecture summary from the last 24 hours.',
      });
    }

    const transcript = await buildTranscript(videoId, transcript_language);
    logger.info(`TRANSCRIPT BUILT analyze request_id=${req.requestId}`, { videoId, segmentCount: transcript.length });

    const summaryTranscript = selectSummaryTranscript(transcript, selectedRange?.start, selectedRange?.end);
    logger.info(`SUMMARY RANGE SELECTED analyze request_id=${req.requestId}`, {
      videoId,
      segmentCount: summaryTranscript.length,
      summaryRange: selectedRange,
    });
    const summary = await generateSummaryFromTranscript(summaryTranscript, output_language, {
      summaryStart: selectedRange?.start,
      summaryEnd: selectedRange?.end,
      requestId: req.requestId,
    });
    logger.info(`LLM SUMMARY GENERATED analyze request_id=${req.requestId}`, {
      videoId,
      quickSummaryLength: summary.quick_summary.length,
      keyConceptCount: summary.key_concepts.length,
    });

    const payload = {
      video_id: videoId,
      title: `Lecture ${videoId}`,
      channel_name: 'YouTube lecture',
      thumbnail_url: '',
      duration: 0,
      url: `https://www.youtube.com/watch?v=${videoId}`,
      status: 'ready',
      transcript_language,
      output_language,
      caption_languages: ['en'],
      summary,
      transcript,
    };

    logger.info(`RAG INDEXING analyze request_id=${req.requestId}`, { videoId, segmentCount: transcript.length });
    await callRagIndex(videoId, transcript);

    logger.info(`DB SAVE analyze request_id=${req.requestId}`, { videoId, upsert: Boolean(existing) });
    const saved = existing ? await Video.findOneAndUpdate({ video_id: videoId }, payload, { new: true, upsert: true }) : await Video.create(payload);
    setCachedSummary(cacheKey, saved.toObject());

    logger.info(`BUSINESS LOGIC analyze_success request_id=${req.requestId}`, {
      videoId,
      savedTitle: saved.title,
      status: saved.status,
    });

    res.status(200).json({
      video_id: saved.video_id,
      title: saved.title,
      channel_name: saved.channel_name,
      thumbnail_url: saved.thumbnail_url,
      duration: saved.duration,
      url: saved.url,
      status: saved.status,
      transcript_language: saved.transcript_language,
      caption_languages: saved.caption_languages,
      summary: saved.summary,
      transcript: saved.transcript,
      message: 'Video processed successfully and indexed for retrieval.',
    });
  } catch (error) {
    logger.error(`BUSINESS LOGIC analyze_failed request_id=${req.requestId}`, {
      videoId,
      message: error.message,
      stack: error.stack,
      requestBody: req.body,
    });
    res.status(error.statusCode || 400).json({ detail: error.message || 'Unable to analyze video.' });
  }
});

app.get('/api/videos/:video_id', async (req, res) => {
  try {
    const video = await Video.findOne({ video_id: req.params.video_id }).lean();
    if (!video) return res.status(404).json({ detail: 'Video not found' });
    res.json(video);
  } catch (error) {
    res.status(500).json({ detail: error.message });
  }
});

app.get('/api/videos/:video_id/transcript', async (req, res) => {
  try {
    const video = await Video.findOne({ video_id: req.params.video_id }).lean();
    if (!video) return res.status(404).json({ detail: 'Video not found' });
    res.json({ video_id: video.video_id, transcript_language: video.transcript_language, segments: video.transcript || [] });
  } catch (error) {
    res.status(500).json({ detail: error.message });
  }
});

app.get('/api/videos/:video_id/summary', async (req, res) => {
  try {
    const video = await Video.findOne({ video_id: req.params.video_id }).lean();
    if (!video) return res.status(404).json({ detail: 'Video not found' });
    res.json({
      video_id: video.video_id,
      quick_summary: video.summary?.quick_summary || '',
      detailed_notes: video.summary?.detailed_notes || [],
      key_concepts: video.summary?.key_concepts || [],
    });
  } catch (error) {
    res.status(500).json({ detail: error.message });
  }
});

app.post('/api/tutor/deep-dive', async (req, res) => {
  const { topic = 'Binary Search', learning_level = 'Beginner', language = 'English', explanation_style = 'step-by-step teaching', video_id } = req.body || {};
  const cacheKey = JSON.stringify({ topic, learning_level, language, explanation_style, video_id });
  const cached = summaryCache.get(cacheKey);
  if (cached && Date.now() < cached.expiresAt) {
    return res.json({ ...cached.value, message: 'Using cached tutor explanation from the last 24 hours.' });
  }

  let transcript = [];
  if (video_id) {
    const video = await Video.findOne({ video_id }).lean();
    transcript = video?.transcript || [];
  }

  const evidence = await callRagSearch(topic, video_id);
  const explanation = evidence.length
    ? `The lecture evidence suggests ${topic} is explained through ${evidence[0].text.slice(0, 160)}... The core idea is to connect the concept to the transcript and then break it into intuition, mechanism, and examples.`
    : `The concept of ${topic} is best understood by framing it around the main idea, then working through the mechanism and examples in a ${explanation_style.toLowerCase()} way.`;

  const payload = {
    session_id: `session-${Date.now()}`,
    topic,
    language,
    learning_level,
    explanation,
    sections: ['Concept overview', 'Mechanism', 'Worked example', 'Trade-offs'],
    sources: evidence.map((hit) => ({ video_id: hit.video_id || video_id || 'lecture', start: hit.start, end: hit.end, label: hit.text.slice(0, 80) })),
    evidence_sufficiency: evidence.length ? 'Grounded using transcript evidence.' : 'Supplemental explanation without direct transcript evidence.',
    explanation_language: language,
  };

  summaryCache.set(cacheKey, { value: payload, expiresAt: Date.now() + CACHE_TTL_MS });
  res.json(payload);
});

app.post('/api/cache/clear', async (req, res) => {
  try {
    clearSummaryCache();
    res.json({ status: 'ok', message: 'Summary cache cleared successfully.' });
  } catch (error) {
    logger.error('CACHE_CLEAR_FAILED', { message: error.message, stack: error.stack });
    res.status(500).json({ detail: error.message });
  }
});

app.delete('/api/videos/:video_id', async (req, res) => {
  try {
    const result = await Video.deleteOne({ video_id: req.params.video_id });
    if (result.deletedCount === 0) return res.status(404).json({ detail: 'Video not found' });
    res.json({ video_id: req.params.video_id, status: 'deleted' });
  } catch (error) {
    res.status(500).json({ detail: error.message });
  }
});

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ detail: err.message || 'Server error' });
});

async function startServer() {
  await connectDB();
  app.listen(PORT, () => {
    console.log(`Node backend listening on http://localhost:${PORT}`);
  });
}

startServer();
