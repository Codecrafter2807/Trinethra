import { useState } from 'react'

export default function GapSection({ items }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="section">
            <button className={`section-toggle ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
                Gap Analysis <span className="count">{items.length}</span>
                <span className="arrow">▼</span>
            </button>
            {open && (
                <div className="section-body">
                    {items.length === 0 && <p className="no-data" style={{ color: 'var(--positive)' }}>No major gaps detected.</p>}
                    {items.map((g, i) => (
                        <div key={i} className={`gap-card gap-${g.severity}`}>
                            <div className="gap-dim">{g.dimension?.replace(/_/g, ' ')}</div>
                            <div className="gap-detail">{g.detail}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}