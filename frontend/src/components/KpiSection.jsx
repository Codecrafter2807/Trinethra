import { useState } from 'react'

export default function KpiSection({ items }) {
    const [open, setOpen] = useState(true)
    return (
        <div className="section">
            <button className={`section-toggle ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
                KPI Mapping <span className="count">{items.length}</span>
                <span className="arrow">▼</span>
            </button>
            {open && (
                <div className="section-body">
                    {items.length === 0 && <p className="no-data">No KPI signals found.</p>}
                    <div className="kpi-grid">
                        {items.map((k, i) => (
                            <div key={i} className="kpi-card">
                                <div className="kpi-name">{k.kpi}</div>
                                <div className="kpi-evidence">{k.evidence}</div>
                                <span className={`kpi-type kpi-${k.system_or_personal}`}>
                                    {k.system_or_personal === 'system' ? '✓ System-driven' : '⚠ Personal effort'}
                                </span>
                                {k.note && <div className="kpi-note">{k.note}</div>}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}