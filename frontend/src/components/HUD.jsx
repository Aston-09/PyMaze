import React from 'react';

/**
 * HUD — Heads-Up Display
 * Persistent header showing player name, HP, Mana, XP, Gold, Level.
 */
export default function HUD({ player }) {
  if (!player) return null;

  const hpFill = Math.min(1, player.hp / 500);
  const manaFill = Math.min(1, player.mana / 200);

  return (
    <header className="hud fade-in">
      <div className="hud-brand">
        <span>⚔</span>
        <span>PyBe</span>
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

      <div className="hud-player-name">
        {player.name}
      </div>
    </header>
  );
}
