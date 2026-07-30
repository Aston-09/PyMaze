import React from 'react';
import './PlayerProfile.css';

export default function PlayerProfile({ player, onClose }) {
  if (!player) return null;

  // Generate last 90 days
  const today = new Date();
  const days = [];
  for (let i = 89; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    
    // Convert to local YYYY-MM-DD to match the backend which uses local date
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    const count = player.activity_log?.[dateStr] || 0;
    
    // Determine color level (0-4)
    let level = 0;
    if (count > 0) level = 1;
    if (count >= 3) level = 2;
    if (count >= 5) level = 3;
    if (count >= 10) level = 4;

    days.push({
      dateStr,
      count,
      level,
      // For tooltip
      displayDate: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    });
  }

  return (
    <div className="profile-overlay fade-in" onClick={onClose}>
      <div className="profile-modal" onClick={e => e.stopPropagation()}>
        <button className="profile-close" onClick={onClose} aria-label="Close Profile">×</button>
        
        <div className="profile-header">
          <div className="profile-name">{player.name}</div>
          <div className="profile-class">Level {player.level} {player.class_name || 'Wanderer'}</div>
        </div>

        <div className="profile-stats-grid">
          <div className="profile-stat-card">
            <div className="profile-stat-label">HP</div>
            <div className="profile-stat-value" style={{ color: 'var(--seal-red)' }}>{player.hp}</div>
          </div>
          <div className="profile-stat-card">
            <div className="profile-stat-label">Mana</div>
            <div className="profile-stat-value" style={{ color: 'var(--ink-blue)' }}>{player.mana}</div>
          </div>
          <div className="profile-stat-card">
            <div className="profile-stat-label">XP</div>
            <div className="profile-stat-value" style={{ color: 'var(--plum)' }}>{player.xp}</div>
          </div>
          <div className="profile-stat-card">
            <div className="profile-stat-label">Gold</div>
            <div className="profile-stat-value" style={{ color: 'var(--gold-bright)' }}>{player.gold}</div>
          </div>
        </div>

        <div className="heatmap-section">
          <div className="heatmap-title">Journey Activity (Last 90 Days)</div>
          <div className="heatmap-grid" style={{ gridTemplateColumns: `repeat(${Math.ceil(90/7)}, minmax(14px, 1fr))`}}>
            {days.map(day => (
              <div 
                key={day.dateStr} 
                className="heatmap-cell" 
                data-level={day.level}
              >
                <div className="heatmap-tooltip">
                  {day.count === 0 ? 'No actions' : `${day.count} actions`} on {day.displayDate}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
