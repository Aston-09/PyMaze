import React, { useState, useEffect } from 'react';

/**
 * SortTypes — match each value to the family it belongs to.
 *
 * Two taps: pick a value, then pick its home. Tap-to-place rather than HTML5
 * drag-and-drop — it works on touch, works from the keyboard, and cannot
 * strand a token mid-drag.
 *
 * The step the player is on is spelled out above the tray, because "select,
 * then place" is invisible until someone has already guessed it. A wrong
 * placement is not punished — it shakes, says so, and stays in play, per the
 * PRD's "fail gracefully" principle.
 */
export default function SortTypes({ config, onSolved }) {
  const bins = config.bins || [];
  const items = config.items || [];

  const [placed, setPlaced] = useState({});   // itemId -> binId
  const [selected, setSelected] = useState(null);
  const [wrongId, setWrongId] = useState(null);
  const [reveal, setReveal] = useState(null);
  const [missed, setMissed] = useState(null);

  const remaining = items.filter((it) => !(it.id in placed));
  const done = remaining.length === 0 && items.length > 0;
  const held = items.find((it) => it.id === selected);

  useEffect(() => {
    if (done) onSolved?.();
  }, [done, onSolved]);

  const placeInto = (bin) => {
    if (!held) {
      // Tapping a home first is the natural guess; say what to do instead of
      // going dead.
      setMissed('Pick a value from the tray above first, then tap its home.');
      return;
    }

    if (held.bin === bin.id) {
      setPlaced((prev) => ({ ...prev, [held.id]: bin.id }));
      setSelected(null);
      setMissed(null);
      setReveal(held.reveal || null);
    } else {
      // Wrong family: shake the token, keep it in play.
      setWrongId(held.id);
      setReveal(null);
      setMissed(`${held.text} does not belong in “${bin.label}”. Try another.`);
      setTimeout(() => setWrongId(null), 420);
    }
  };

  return (
    <>
      <p className="sort-step">
        {done ? 'Every value has found its family.'
          : held ? <>Step 2 — where does <strong>{held.text}</strong> belong?</>
          : 'Step 1 — tap a value below.'}
      </p>

      <div className="sort-tray">
        {remaining.length === 0 ? (
          <span className="chest-caption">Tray empty.</span>
        ) : (
          remaining.map((item) => (
            <button
              key={item.id}
              className={`token ${selected === item.id ? 'is-selected' : ''} ${wrongId === item.id ? 'is-wrong' : ''}`}
              onClick={() => { setSelected(selected === item.id ? null : item.id); setMissed(null); }}
              aria-pressed={selected === item.id}
            >
              {item.text}
            </button>
          ))
        )}
      </div>

      <div className="bin-grid">
        {bins.map((bin) => {
          const contents = items.filter((it) => placed[it.id] === bin.id);
          return (
            <button
              key={bin.id}
              className={`bin ${held ? 'is-target' : ''} ${contents.length ? 'is-full' : ''}`}
              onClick={() => placeInto(bin)}
              aria-label={held ? `Place ${held.text} into ${bin.label}` : bin.label}
            >
              <span className="bin-label">{bin.label}</span>
              <span className="bin-hint">{bin.hint}</span>
              <span className="bin-items">
                {contents.map((it) => (
                  <span key={it.id} className="token">{it.text}</span>
                ))}
              </span>
            </button>
          );
        })}
      </div>

      {missed && <p className="sort-miss">{missed}</p>}
      {reveal && <p className="interaction-resolve">{reveal}</p>}

      <p className="interaction-progress">
        {done ? 'Sorting complete' : `${remaining.length} value${remaining.length === 1 ? '' : 's'} remaining`}
      </p>
    </>
  );
}
