import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

/**
 * HUD — Heads-Up Display
 * Persistent header showing player name, HP, Mana, XP, Gold, Level.
 */
export default function HUD({ player, isSidebarOpen, toggleSidebar, onOpenProfile }) {
  const { logout } = useContext(AuthContext);

  if (!player) return null;

  const hpFill = Math.min(1, player.hp / 500);
  const manaFill = Math.min(1, player.mana / 200);

  return (
    <header className="hud fade-in">
      <div className="hud-brand" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button 
          onClick={toggleSidebar} 
          className="btn btn-ghost" 
          style={{ minHeight: '32px', padding: '0.35rem 0.6rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          title={isSidebarOpen ? "Hide Journey" : "Show Journey"}
        >
          {isSidebarOpen ? '📖' : '📘'}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span>⚔</span>
          <span>PyMaze</span>
        </div>
      </div>

      <div className="hud-stats">
        {/* HP */}
        <div className="hud-stat">
          <span className="stat-icon">❤️</span>
          <span className="stat-value">{player.hp}</span>
          <div className="stat-bar-container">
            <div className="stat-bar-fill stat-bar-hp" style={{ transform: `scaleX(${hpFill})` }} />
          </div>
        </div>

        {/* Mana */}
        <div className="hud-stat">
          <span className="stat-icon">🔷</span>
          <span className="stat-value">{player.mana}</span>
          <div className="stat-bar-container">
            <div className="stat-bar-fill stat-bar-mana" style={{ transform: `scaleX(${manaFill})` }} />
          </div>
        </div>

        {/* XP */}
        <div className="hud-stat">
          <span className="stat-icon">⭐</span>
          <span className="stat-value">{player.xp} XP</span>
        </div>

        {/* Gold */}
        <div className="hud-stat">
          <span className="stat-icon">💰</span>
          <span className="stat-value">{player.gold}</span>
        </div>

        {/* Level */}
        <div className="hud-stat">
          <span className="stat-icon">🏅</span>
          <span className="stat-value">Lv.{player.level}</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div 
          className="hud-player-name" 
          onClick={onOpenProfile}
          style={{ cursor: 'pointer', transition: 'background 0.2s', title: 'View Profile' }}
          onMouseOver={e => e.currentTarget.style.background = 'var(--accent-hover)'}
          onMouseOut={e => e.currentTarget.style.background = 'var(--seal-red)'}
        >
          {player.name}
        </div>
        <button 
          onClick={logout} 
          className="btn btn-ghost"
          style={{ minHeight: '30px', padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
          title="Logout"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
