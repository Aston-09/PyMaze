import React, { useState, useCallback, useEffect, useRef } from 'react';
import WIDGETS from './registry';
import useAdvanceKey from '../../utils/useAdvanceKey';

import { apiFetch } from '../../utils/api';

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
  const footerRef = useRef(null);

  const Widget = WIDGETS[interaction?.widget];

  // Enter finishes the beat once it is actually solved.
  useAdvanceKey(onComplete, solved);

  // A long puzzle can push its own Continue below the fold. Focusing it both
  // scrolls it into view and puts Enter on it — otherwise the key would land
  // on whichever puzzle button was clicked last and re-fire it.
  useEffect(() => {
    if (solved) footerRef.current?.focus({ preventScroll: false });
  }, [solved]);

  const handleSolved = useCallback(async () => {
    // Guard against a widget firing onSolved twice — the backend is
    // idempotent, but the XP flourish should only play once.
    if (solved) return;
    setSolved(true);

    try {
      const res = await apiFetch(`/interaction/complete`, {
        method: 'POST',
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
          <button className="btn btn-primary" ref={footerRef} onClick={onComplete}>Continue →</button>
          <span className="advance-hint">or press Enter</span>
        </div>
      )}

      {xpFloat && <div className="xp-float">{xpFloat}</div>}
    </div>
  );
}
