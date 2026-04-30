import { useState, useEffect } from 'react'
import axios from 'axios'
import ScoreBlock from './components/ScoreBlock'
import EvidenceSection from './components/EvidenceSection'
import KpiSection from './components/KpiSection'
import GapSection from './components/GapSection'
import QuestionsSection from './components/QuestionsSection'
import './App.css'

const API = 'http://localhost:8000/api'

export default function App() {
  const [transcript, setTranscript] = useState('')
  const [model, setModel] = useState('llama3.2:latest')
  const [samples, setSamples] = useState([])
  const [health, setHealth] = useState('checking...')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    checkHealth()
    loadSamples()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  async function checkHealth() {
    try {
      const { data } = await axios.get(`${API}/health/`)
      setHealth(data.ollama === 'connected' ? 'ok' : 'err')
    } catch {
      setHealth('err')
    }
  }

  async function loadSamples() {
    try {
      const { data } = await axios.get(`${API}/samples/`)
      setSamples(data.transcripts)
    } catch { }
  }

  async function runAnalysis() {
    if (!transcript.trim()) return alert('Paste a transcript first.')
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const { data } = await axios.post(`${API}/analyze/`, { transcript, model })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.error || 'Cannot reach backend. Is Django running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="logo">Trinethra <span>Supervisor Feedback Analyzer</span></div>
        <div className={`health-badge ${health}`}>
          {health === 'ok' ? 'ollama ✓' : health === 'err' ? 'ollama offline' : 'checking...'}
        </div>
      </header>

      <div className="layout">
        {/* INPUT PANEL */}
        <div className="panel input-panel">
          <div className="panel-header">
            Supervisor Transcript
            <span className="char-count">{transcript.length.toLocaleString()} chars</span>
          </div>

          <div className="sample-bar">
            <span className="sample-label">Load sample:</span>
            {samples.map(s => (
              <button key={s.id} className="sample-btn" title={s.trap}
                onClick={() => setTranscript(s.transcript)}>
                {s.fellow_name}
              </button>
            ))}
          </div>

          <textarea
            className="transcript-input"
            value={transcript}
            onChange={e => setTranscript(e.target.value)}
            placeholder="Paste the supervisor's transcript here..."
          />

          <div className="input-footer">
            <input
              className="model-input"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="Ollama model (e.g. llama3.2)"
            />
            <button className="run-btn" onClick={runAnalysis} disabled={loading}>
              {loading ? 'Analyzing...' : 'Run Analysis →'}
            </button>
          </div>
        </div>

        {/* OUTPUT PANEL */}
        <div className="panel output-panel">
          <div className="panel-header">Analysis Output</div>

          {!loading && !result && !error && (
            <div className="placeholder">
              <div className="placeholder-icon">◎</div>
              <p>Paste a transcript and click <strong>Run Analysis</strong>.<br />
                Or load one of the sample transcripts.</p>
            </div>
          )}

          {loading && (
            <div className="loading">
              <div className="spinner" />
              <p>Running through {model}…<br />
                <span className="loading-note">30–90 seconds depending on your machine.</span></p>
            </div>
          )}

          {error && <div className="error-box">⚠ {error}</div>}

          {result && (
            <div className="analysis">
              <ScoreBlock score={result.analysis.score} />
              <EvidenceSection items={result.analysis.evidence || []} />
              <KpiSection items={result.analysis.kpi_mapping || []} />
              <GapSection items={result.analysis.gaps || []} />
              <QuestionsSection items={result.analysis.follow_up_questions || []} />
              <div className="analysis-footer">
                analyzed via {result.model_used} · draft only — intern review required
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
