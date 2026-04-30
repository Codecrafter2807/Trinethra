import { useState } from 'react'

export default function QuestionsSection({ items }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="section">
            <button className={`section-toggle ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
                Follow-up Questions <span className="count">{items.length}</span>
                <span className="arrow">▼</span>
            </button>
            {open && (
                <div className="section-body">
                    {items.map((q, i) => (
                        <div key={i} className="question-card">
                            <div className="question-text">{i + 1}. {q.question}</div>
                            <div className="question-meta">
                                <strong>Targets:</strong> {q.target_gap?.replace(/_/g, ' ')}<br />
                                <strong>Looking for:</strong> {q.looking_for}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}