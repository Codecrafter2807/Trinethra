import { useState } from 'react'

export default function EvidenceSection({ items }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="section">
            <button className={`section-toggle ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
                Evidence Extracted <span className="count">{items.length}</span>
                <span className="arrow">▼</span>
            </button>
            {open && (
                <div className="section-body">
                    {items.map((e, i) => (
                        <div key={i} className="evidence-card">
                            <div className="evidence-header">
                                <span className={`tag tag-${e.signal}`}>{e.signal}</span>
                                <span className={`tag tag-${e.layer?.replace('_', '')}`}>
                                    {e.layer === 'layer_2' ? 'Layer 2 — Systems' : 'Layer 1 — Execution'}
                                </span>
                                <span className="tag tag-dim">{e.dimension?.replace(/_/g, ' ')}</span>
                            </div>
                            <div className="evidence-quote">"{e.quote}"</div>
                            <div className="evidence-interp">{e.interpretation}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}