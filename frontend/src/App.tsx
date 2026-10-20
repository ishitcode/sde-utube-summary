import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  BookOpen,
  CheckCircle2,
  FolderOpen,
  History,
  LayoutGrid,
  PlayCircle,
  Settings,
  Sparkles,
} from 'lucide-react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from './lib/api'
import type { Lecture } from './types'
import './App.css'

const chartData = [
  { name: 'Mon', score: 62 },
  { name: 'Tue', score: 68 },
  { name: 'Wed', score: 73 },
  { name: 'Thu', score: 79 },
  { name: 'Fri', score: 84 },
  { name: 'Sat', score: 88 },
]

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid },
  { to: '/import', label: 'Import Lecture', icon: FolderOpen },
  { to: '/workspace', label: 'Lecture Workspace', icon: BookOpen },
  { to: '/history', label: 'Study History', icon: History },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function App() {
  const [lectures, setLectures] = useState<Lecture[]>([])
  const [selectedLecture, setSelectedLecture] = useState<Lecture | null>(null)
  const [health, setHealth] = useState<{ status?: string; service?: string }>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hydrateLecture = async (videoId: string): Promise<Lecture | null> => {
    try {
      const { data } = await api.get(`/videos/${videoId}`)
      return data
    } catch (error) {
      console.warn(`Unable to hydrate lecture ${videoId}`, error)
      return null
    }
  }

  const fetchHistory = async () => {
    try {
      const { data } = await api.get('/history')
      const items = data.items || []
      setLectures(items)
      if (items[0]) {
        const hydrated = await hydrateLecture(items[0].video_id)
        setSelectedLecture((current) => current ?? hydrated ?? items[0])
      }
    } catch (error) {
      console.warn('History unavailable', error)
    }
  }

  const fetchHealth = async () => {
    try {
      const { data } = await api.get('/health')
      setHealth(data)
    } catch (error) {
      console.warn('Health check failed', error)
    }
  }

  useEffect(() => {
    void fetchHealth()
    void fetchHistory()
  }, [])

  const currentLecture = useMemo(() => selectedLecture ?? lectures[0] ?? null, [selectedLecture, lectures])

  const handleSelectLecture = async (lecture: Lecture) => {
    const hydrated = await hydrateLecture(lecture.video_id)
    setSelectedLecture(hydrated ?? lecture)
  }

  const handleAnalyzeUrl = async (url: string, summaryStart?: number, summaryEnd?: number, refresh = true) => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post('/videos/analyze', {
        url,
        transcript_language: 'auto',
        output_language: 'English',
        summary_start: summaryStart,
        summary_end: summaryEnd,
        refresh,
      })
      setSelectedLecture(data)
      setLectures((prev) => {
        const next = [data, ...prev.filter((item) => item.video_id !== data.video_id)]
        return next
      })
      return data
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to analyze this video URL.')
      return null
    } finally {
      setLoading(false)
    }
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand-block">
            <div className="brand-icon">
              <Sparkles size={18} />
            </div>
            <div>
              <p className="eyebrow">AI learning lab</p>
              <h1>StudyFlow</h1>
            </div>
          </div>

          <nav className="sidebar-nav">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={16} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="sidebar-card">
            <p className="eyebrow">System status</p>
            <div className="status-row">
              <span className={`status-dot ${health.status === 'ok' ? 'online' : ''}`} />
              <span>{health.status === 'ok' ? 'Backend online' : 'Standby'}</span>
            </div>
            <small>{health.service || 'YouTube summary API'}</small>
          </div>
        </aside>

        <main className="main-panel">
          <Routes>
            <Route
              path="/"
              element={
                <DashboardPage
                  lectures={lectures}
                  currentLecture={currentLecture}
                  health={health}
                  onSelectLecture={handleSelectLecture}
                />
              }
            />
            <Route
              path="/import"
              element={<ImportPage loading={loading} error={error} onAnalyze={handleAnalyzeUrl} />}
            />
            <Route
              path="/workspace"
              element={<LectureWorkspacePage lecture={currentLecture} />}
            />
            <Route path="/history" element={<HistoryPage lectures={lectures} />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

function DashboardPage({
  lectures,
  currentLecture,
  health,
  onSelectLecture,
}: {
  lectures: Lecture[]
  currentLecture: Lecture | null
  health: { status?: string; service?: string }
  onSelectLecture: (lecture: Lecture) => Promise<void>
}) {
  const progress = 78

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Learning dashboard</h2>
        </div>
      </header>

      <section className="stats-grid">
        <StatCard label="Lectures processed" value={String(lectures.length || 1)} icon={<PlayCircle size={18} />} />
        <StatCard label="Review streak" value="12 days" icon={<CheckCircle2 size={18} />} />
        <StatCard label="Study sessions" value="9" icon={<BookOpen size={18} />} />
        <StatCard label="Concept recall" value={`${progress}%`} icon={<Activity size={18} />} />
      </section>

      <section className="content-grid two-column">
        <div className="panel">
          <div className="panel-heading">
            <h3>Study momentum</h3>
            <span className="badge">Weekly</span>
          </div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="4 4" stroke="#2b3748" />
                <XAxis dataKey="name" stroke="#9fb3c8" />
                <YAxis stroke="#9fb3c8" domain={[0, 100]} />
                <Line type="monotone" dataKey="score" stroke="#a78bfa" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Recently studied</h3>
            <span className="badge">Live</span>
          </div>
          <div className="lecture-list">
            {(lectures.length ? lectures : [{ video_id: 'demo', title: 'No lectures yet', status: 'idle' }]).map((item) => (
              <button
                key={item.video_id}
                type="button"
                className={`lecture-row ${currentLecture?.video_id === item.video_id ? 'selected' : ''}`}
                onClick={() => void onSelectLecture(item)}
              >
                <div className="lecture-thumb small" />
                <div>
                  <strong>{item.title || 'Untitled lecture'}</strong>
                  <small>{item.status || 'Ready to import'}</small>
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h3>Focus lecture</h3>
          <span className="badge">{health.status === 'ok' ? 'Connected' : 'Offline'}</span>
        </div>
        <div className="focus-card">
          <div className="focus-copy">
            <p className="eyebrow">Current topic</p>
            <h3>{currentLecture?.title || 'Import your next YouTube lecture'}</h3>
            <p>
              {currentLecture?.summary?.quick_summary ||
                'The backend is ready to validate URLs, fetch transcript data, and generate a structured lecture summary.'}
            </p>
          </div>
          <div className="focus-meta">
            <span>{currentLecture?.channel_name || 'No channel metadata yet'}</span>
            <span>{currentLecture?.transcript_language || 'Auto transcript language'}</span>
            <span>{currentLecture?.duration ? `${Math.round(currentLecture.duration / 60)} min` : 'Not loaded yet'}</span>
          </div>
        </div>
      </section>
    </div>
  )
}

function ImportPage({
  loading,
  error,
  onAnalyze,
}: {
  loading: boolean
  error: string | null
  onAnalyze: (url: string, summaryStart?: number, summaryEnd?: number) => Promise<any>
}) {
  const [url, setUrl] = useState('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
  const [summaryStart, setSummaryStart] = useState('')
  const [summaryEnd, setSummaryEnd] = useState('')
  const [rangeError, setRangeError] = useState<string | null>(null)
  const [result, setResult] = useState<Lecture | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setRangeError(null)
    if (Boolean(summaryStart) !== Boolean(summaryEnd)) {
      setRangeError('Enter both start and end times, or leave both blank.')
      return
    }

    let startSeconds: number | undefined
    let endSeconds: number | undefined
    if (summaryStart && summaryEnd) {
      const parsedStart = parseTimeInput(summaryStart)
      const parsedEnd = parseTimeInput(summaryEnd)
      if (parsedStart === null || parsedEnd === null || parsedEnd <= parsedStart) {
        setRangeError('Use valid times in mm:ss or hh:mm:ss format, with the end after the start.')
        return
      }
      startSeconds = parsedStart
      endSeconds = parsedEnd
    }

    const outcome = await onAnalyze(url, startSeconds, endSeconds)
    if (outcome) setResult(outcome)
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Import</p>
          <h2>YouTube lecture intake</h2>
        </div>
      </header>

      <div className="panel large">
        <form className="import-form" onSubmit={handleSubmit}>
          <label htmlFor="video-url">YouTube URL</label>
          <div className="input-row">
            <input
              id="video-url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
            <button type="submit" className="primary-button" disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze lecture'}
            </button>
          </div>
          <p className="eyebrow">Summarize a section (optional)</p>
          <div className="input-row">
            <label htmlFor="summary-start">
              Start time
              <input
                id="summary-start"
                inputMode="numeric"
                placeholder="00:00"
                value={summaryStart}
                onChange={(event) => setSummaryStart(event.target.value)}
              />
            </label>
            <label htmlFor="summary-end">
              End time
              <input
                id="summary-end"
                inputMode="numeric"
                placeholder="05:30"
                value={summaryEnd}
                onChange={(event) => setSummaryEnd(event.target.value)}
              />
            </label>
          </div>
          {(rangeError || error) && <p className="error-message">{rangeError || error}</p>}
        </form>
      </div>

      {result && (
        <section className="panel">
          <div className="panel-heading">
            <h3>Processing result</h3>
            <span className="badge">Verified</span>
          </div>
          <div className="result-grid">
            <div>
              <p className="eyebrow">Title</p>
              <h3>{result.title || 'Imported lecture'}</h3>
            </div>
            <div>
              <p className="eyebrow">Language</p>
              <h3>{result.transcript_language || 'Auto-detected'}</h3>
            </div>
            <div>
              <p className="eyebrow">Status</p>
              <h3>{result.status}</h3>
            </div>
          </div>
          <p>{result.message}</p>
        </section>
      )}
    </div>
  )
}

function LectureWorkspacePage({ lecture }: { lecture: Lecture | null }) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>{lecture?.title || 'Lecture workspace'}</h2>
        </div>
      </header>

      <section className="content-grid two-column">
        <div className="panel">
          <div className="panel-heading">
            <h3>Summary</h3>
            <span className="badge">
              {lecture?.summary?.summary_range
                ? `${formatTimestamp(lecture.summary.summary_range.start)} - ${formatTimestamp(lecture.summary.summary_range.end)}`
                : 'Structured'}
            </span>
          </div>
          <p>{lecture?.summary?.quick_summary || 'No summary available yet'}</p>
          <ul className="list-block">
            {(lecture?.summary?.key_concepts || ['Lecture overview', 'Deep dive learning', 'Revision']).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Transcript</h3>
            <span className="badge">Timestamped</span>
          </div>
          <div className="transcript-list">
            {(lecture?.transcript || [{ text: 'Transcript will appear once the lecture is processed.', start: 0, end: 30 }]).map((segment, index) => (
              <div className="segment-row" key={`${segment.start}-${index}`}>
                <span>{formatTimestamp(segment.start)}</span>
                <p>{segment.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

function HistoryPage({ lectures }: { lectures: Lecture[] }) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">History</p>
          <h2>Study history</h2>
        </div>
      </header>

      <section className="panel">
        <div className="lecture-list history-list">
          {(lectures.length ? lectures : [{ video_id: 'no-history', title: 'No processed lectures yet', status: 'empty' }]).map((lecture) => (
            <div key={lecture.video_id} className="history-row">
              <div className="history-thumb" />
              <div>
                <strong>{lecture.title || 'Untitled lecture'}</strong>
                <small>{lecture.status || 'Ready to learn'}</small>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function SettingsPage() {
  const handleClearCache = async () => {
    try {
      await api.post('/cache/clear')
      window.alert('Summary cache cleared successfully.')
    } catch (error: any) {
      window.alert(error?.response?.data?.detail || 'Unable to clear the cache.')
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Preferences</p>
          <h2>Learning settings</h2>
        </div>
      </header>

      <section className="settings-grid">
        <div className="panel">
          <h3>Output language</h3>
          <ul className="list-block">
            <li>English</li>
            <li>Hinglish</li>
            <li>Hindi</li>
          </ul>
        </div>
        <div className="panel">
          <h3>Retrieval stack</h3>
          <ul className="list-block">
            <li>Hybrid Dense + BM25</li>
            <li>Transcript chunking enabled</li>
            <li>Qdrant-ready indexing</li>
          </ul>
        </div>
        <div className="panel">
          <h3>AI configuration</h3>
          <ul className="list-block">
            <li>Gemini provider</li>
            <li>Multilingual embedding model</li>
            <li>API keys stored server-side only</li>
          </ul>
        </div>
      </section>

      <section className="panel" style={{ marginTop: '1.5rem' }}>
        <div className="panel-heading">
          <h3>Cache control</h3>
        </div>
        <button type="button" className="primary-button" onClick={handleClearCache}>
          Clear summary cache
        </button>
      </section>
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="stat-card panel">
      <div className="stat-icon">{icon}</div>
      <div>
        <strong>{value}</strong>
        <small>{label}</small>
      </div>
    </div>
  )
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const mins = String(Math.floor(total / 60)).padStart(2, '0')
  const secs = String(total % 60).padStart(2, '0')
  return `${mins}:${secs}`
}

function parseTimeInput(value: string): number | null {
  const parts = value.split(':')
  if (parts.length < 2 || parts.length > 3 || parts.some((part) => !/^\d+$/.test(part))) return null

  const numbers = parts.map(Number)
  if (numbers.slice(1).some((part) => part >= 60)) return null
  return numbers.reduce((total, part) => total * 60 + part, 0)
}

export default App
