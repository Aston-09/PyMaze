import React, { useState } from 'react';
import { ASSET_URL } from '../config';
import { apiFetch } from '../utils/api';

/**
 * AppearancePicker — the one-time "choose your look" gate.
 *
 * The player's own art comes in two sprite sets (assets/characters/player/
 * male|female/). This is the only place that choice gets made; every scene
 * afterward just writes `background: player` and the backend resolves it
 * against whatever was picked here (see `_resolve_player_art` in main.py).
 *
 * Props:
 *   onChosen: called with the updated player once the pick is saved
 */
export default function AppearancePicker({ onChosen }) {
  const [saving, setSaving] = useState(false);

  const choose = async (gender) => {
    setSaving(true);
    try {
      const res = await apiFetch('/player/appearance', {
        method: 'POST',
        body: JSON.stringify({ gender }),
      });
      if (!res.ok) throw new Error(`appearance save failed (${res.status})`);
      const data = await res.json();
      onChosen(data.player);
    } catch (err) {
      console.error('Failed to set appearance:', err);
      setSaving(false);
    }
  };

  return (
    <div className="appearance-gate fade-in">
      <div className="appearance-card">
        <h2>Choose Your Look</h2>
        <p className="appearance-hint">
          Every reflection this world shows you — mirrors, portraits, the Sage's glass —
          will use this face.
        </p>
        <div className="appearance-options">
          {['male', 'female'].map((gender) => (
            <button
              key={gender}
              type="button"
              className="appearance-option"
              disabled={saving}
              onClick={() => choose(gender)}
            >
              <span
                className="appearance-portrait"
                style={{
                  backgroundImage: `url("${ASSET_URL}/characters/player/${gender}/frame_1.jpg")`,
                }}
              />
              <span className="appearance-label">{gender === 'male' ? 'Male' : 'Female'}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
