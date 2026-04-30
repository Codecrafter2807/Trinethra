export default function ScoreBlock({ score }) {
    if (!score) return null
    const bandClass = score.band?.toLowerCase().includes('need') ? 'band-need'
        : score.band?.toLowerCase().includes('prod') ? 'band-prod' : 'band-perf'

    return (
        <div className={`score-block ${bandClass}`}>
            <div className="score-circle">
                <span className="score-num">{score.value}</span>
                <span className="score-denom">/ 10</span>
            </div>
            <div className="score-info">
                <div className="score-label">{score.label}</div>
                <div className="score-band">{score.band} band</div>
                <span className="confidence-pill">Confidence: {score.confidence}</span>
                {score.biases_detected?.length > 0 && (
                    <div className="bias-alerts">
                        {score.biases_detected.map((b, i) => (
                            <div key={i} className="bias-alert">⚠ {b}</div>
                        ))}
                    </div>
                )}
                <div className="score-justification">{score.justification}</div>
            </div>
        </div>
    )
}