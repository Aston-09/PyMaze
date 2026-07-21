

export default function DragonOverlay({ dragonData, onDismiss }) {
  if (!dragonData) return null;

  return (
    <div className="dragon-overlay" onClick={onDismiss}>
      <div className="dragon-card" onClick={(e) => e.stopPropagation()}>
        <div className="dragon-title">
          {dragonData.type === 'weak' && '🐉 Dragon\'s Blessing'}
          {dragonData.type === 'balanced' && '🐉 Dragon\'s Recognition'}
          {dragonData.type === 'overpowered' && '🐉 Trial of the Dragon'}
        </div>
        <div className="dragon-text">
          {dragonData.narrative.split('\n').map((line, i) => (
            <div key={i}>
              {line.startsWith('"') ? (
                <span className="dragon-quote">{line}</span>
              ) : (
                <span>{line}</span>
              )}
            </div>
          ))}
        </div>
        {dragonData.type === 'weak' && (
          <div className="reward-achievement">
            🏆 Achievement: DRAGON'S BLESSING
          </div>
        )}
        {dragonData.type === 'balanced' && (
          <div className="reward-achievement">
            🏆 Achievement: DRAGON'S RECOGNITION
          </div>
        )}
        {dragonData.type === 'overpowered' && (
          <div className="reward-achievement is-warning">
            ⚠️ Dragon Trial Required!
          </div>
        )}
        <button className="btn btn-primary" style={{ marginTop: '1.5rem', width: '100%' }} onClick={onDismiss}>
          Continue →
        </button>
      </div>
    </div>
  );
}
