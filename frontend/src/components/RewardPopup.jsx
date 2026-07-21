import React from 'react';

/**
 * RewardPopup — Animated overlay showing earned rewards after a challenge.
 *
 * Props:
 *   reward: { xp, gold, title, achievement }
 *   statBonuses: { int_bonus, wis_bonus, dex_bonus }
 *   onDismiss: called when the user clicks Continue
 */
export default function RewardPopup({ reward, statBonuses, onDismiss }) {
  return (
    <div className="reward-overlay" onClick={onDismiss}>
      <div className="reward-card" onClick={(e) => e.stopPropagation()}>
        <div className="reward-title">🎉 Quest Complete!</div>

        {reward?.xp > 0 && (
          <div className="reward-item reward-xp">
            <span className="reward-icon">⭐</span>
            +{reward.xp} XP
          </div>
        )}

        {reward?.gold > 0 && (
          <div className="reward-item reward-gold">
            <span className="reward-icon">💰</span>
            +{reward.gold} Gold
          </div>
        )}

        {statBonuses?.int_bonus > 0 && (
          <div className="reward-item reward-int">
            <span className="reward-icon">🧠</span>
            +{statBonuses.int_bonus} Intelligence
          </div>
        )}

        {statBonuses?.wis_bonus > 0 && (
          <div className="reward-item reward-wis">
            <span className="reward-icon">📚</span>
            +{statBonuses.wis_bonus} Wisdom
          </div>
        )}

        {statBonuses?.dex_bonus > 0 && (
          <div className="reward-item reward-dex">
            <span className="reward-icon">⚡</span>
            +{statBonuses.dex_bonus} Dexterity
          </div>
        )}

        {reward?.title && (
          <div className="reward-achievement">
            🏅 Title Unlocked: {reward.title}
          </div>
        )}

        {reward?.achievement && (
          <div className="reward-achievement">
            🏆 Achievement: {reward.achievement}
          </div>
        )}

        <button className="btn btn-primary" style={{ marginTop: '1.5rem', width: '100%' }} onClick={onDismiss}>
          Continue →
        </button>
      </div>
    </div>
  );
}
