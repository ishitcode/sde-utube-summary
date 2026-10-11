const mongoose = require('mongoose');

const transcriptSegmentSchema = new mongoose.Schema(
  {
    text: { type: String, required: true },
    start: { type: Number, default: 0 },
    end: { type: Number, default: 0 },
    language: { type: String, default: 'en' },
    source: { type: String, default: 'youtube-transcript' },
  },
  { _id: false }
);

const videoSchema = new mongoose.Schema(
  {
    video_id: { type: String, required: true, unique: true, index: true },
    title: { type: String, default: 'Untitled lecture' },
    channel_name: { type: String, default: 'Unknown channel' },
    thumbnail_url: { type: String, default: '' },
    duration: { type: Number, default: 0 },
    url: { type: String, required: true },
    status: { type: String, default: 'ready' },
    transcript_language: { type: String, default: 'auto' },
    output_language: { type: String, default: 'English' },
    caption_languages: [{ type: String }],
    summary: {
      quick_summary: { type: String, default: '' },
      detailed_notes: [{ type: String }],
      key_concepts: [{ type: String }],
      timestamp_references: [
        {
          start: Number,
          end: Number,
          label: String,
        },
      ],
    },
    transcript: [transcriptSegmentSchema],
    created_at: { type: Date, default: Date.now },
    updated_at: { type: Date, default: Date.now },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Video', videoSchema);
