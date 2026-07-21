
export default function EndScreen({ player }) {
  return (
    <div className="main-content" style={{ gridTemplateColumns: '1fr' }}>
      <div className="panel" style={{ maxWidth: 600, margin: '0 auto', width: '100%', textAlign: 'center', justifyContent: 'center' }}>
        <h1>To Be Continued...</h1>
        <p style={{ fontSize: '1.1rem' }}>
          Your journey is just beginning, <strong style={{ color: 'var(--text-gold)' }}>{player?.name || 'Traveler'}</strong>.
        </p>
        <p>More challenges and chapters are coming soon.</p>
      </div>
    </div>
  );
}
