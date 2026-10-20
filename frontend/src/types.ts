export type Lecture = {
  video_id: string
  title?: string | null
  channel_name?: string | null
  thumbnail_url?: string | null
  duration?: number | null
  url?: string
  status?: string
  transcript_language?: string | null
  caption_languages?: string[]
  summary?: {
    quick_summary?: string
    detailed_notes?: string[]
    key_concepts?: string[]
    timestamp_references?: Array<{ start: number; end: number; label: string }>
    summary_range?: { start: number; end: number } | null
  }
  transcript?: Array<{ text: string; start: number; end: number; language?: string | null; source?: string | null }>
  message?: string
}

export type TutorSession = {
  session_id: string
  topic: string
  learning_level: string
  language: string
  explanation: string
  sections: string[]
  sources: Array<{ label?: string; start?: number; end?: number }>
  evidence_sufficiency: string
}
