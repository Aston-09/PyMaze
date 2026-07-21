import React, { useState, useCallback } from 'react';
import WIDGETS from './registry';

import { API_URL } from '../../config';

/**
 * InteractionStage — frame around a single playable beat.
 *
 * Owns everything common to interactions: the title and prompt, the reward
 * call once solved, the XP flourish, and the gate that stops the learner
 * advancing before they have actually done the thing.
 *
 * Props:
 *   interaction: the definition from the API (already player-rendered)
 *   onComplete:  advance to the next beat
 *   setPlayer:   lift the updated player state so the HUD reflects the reward
 */
export default function InteractionStage({ interaction, onComplete, setPlayer }) {
  const [solved, setSolved] = useState(false);
  const [xpFloat, setXpFloat] = useState(null);

  const Widget = WIDGETS[interaction?.widget];

  const handleSolved = useCallback(async () => {
    // Guard against a widget firing onSolved twice — the backend is
    // idempotent, but the XP flourish should only play once.
    if (solved) return;
    setSolved(true);

    try {
      const res = await fetch(`${API_URL}/interaction/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interaction_id: interaction.interaction_id }),
      });
      const data = await res.json();
      if (data.player) setPlayer?.(data.player);
      if (data.awarded && data.reward?.xp > 0) {
        setXpFloat(`+${data.reward.xp} XP`);
        setTimeout(() => setXpFloat(null), 1600);
      }
    } catch {
      // A rewards outage must never strand the learner mid-chapter.
    }
  }, [solved, interaction, setPlayer]);

  if (!Widget) {
    // An unrenderable beat is a content bug, not a dead end — let them pass.
    return (
      <div className="interaction-stage">
        <p className="interaction-prompt">
          This beat cannot be displayed (unknown widget “{interaction?.widget}”).
        </p>
        <button className="btn btn-primary" onClick={onComplete}>Continue →</button>
      </div>
    );
  }

  return (
    <div className="interaction-stage fade-in">
      {interaction.title && <h2 className="interaction-title">{interaction.title}</h2>}
      {interaction.prompt && <p className="interaction-prompt">{interaction.prompt}</p>}

      <Widget config={interaction.config || {}} onSolved={handleSolved} />

      {solved && (
        <div className="interaction-footer">
          <button className="btn btn-primary" onClick={onComplete}>Continue →</button>
        </div>
      )}

      {xpFloat && <div className="xp-float">{xpFloat}</div>}
    </div>
  );
}
