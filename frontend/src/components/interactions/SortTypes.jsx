import React, { useState, useEffect } from 'react';

/**
 * SortTypes — place each value into the type family it belongs to.
 *
 * Select a value, then choose its family. Tap-to-place rather than HTML5
 * drag-and-drop: it works on touch, works from the keyboard, and cannot
 * strand a token mid-drag.
 *
 * A wrong placement is not punished — it shakes, explains itself, and lets
 * the learner try again, per the PRD's "fail gracefully" principle.
 */
export default function SortTypes({ config, onSolved }) {
  const bins = config.bins || [];
  const items = config.items || [];

  const [placed, setPlaced] = useState({});   // itemId -> binId
  const [selected, setSelected] = useState(null);
  const [wrongId, setWrongId] = useState(null);
  const [reveal, setReveal] = useState(null);

  const remaining = items.filter((it) => !(it.id in placed));
  const done = remaining.length === 0 && items.length > 0;

  useEffect(() => {
    if (done) onSolved?.();
  }, [done, onSolved]);

  const placeInto = (binId) => {
    if (!selected) return;
    const item = items.find((it) => it.id === selected);
    if (!item) return;

    if (item.bin === binId) {
      setPlaced((prev) => ({ ...prev, [item.id]: binId }));
      setSelected(null);
      setReveal(item.reveal || null);
    } else {
      // Wrong family: shake the token, keep it in play.
      setWrongId(item.id);
      setReveal(null);
      setTimeout(() => setWrongId(null), 420);
    }
  };

  return (
    <>
      <div className="sort-tray">
        {remaining.length === 0 ? (
          <span className="chest-caption">Every value has found its family.</span>
        ) : (
          remaining.map((item) => (
            <button
              key={item.id}
              className={`token ${selected === item.id ? 'is-selected' : ''} ${wrongId === item.id ? 'is-wrong' : ''}`}
              onClick={() => setSelected(selected === item.id ? null : item.id)}
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
              className={`bin ${selected ? 'is-target' : ''} ${contents.length ? 'is-full' : ''}`}
              onClick={() => placeInto(bin.id)}
              disabled={!selected}
              aria-label={`Place the selected value into ${bin.label}`}
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

      {reveal && <p className="interaction-resolve">{reveal}</p>}

      <p className="interaction-progress">
        {done ? 'Sorting complete' : `${remaining.length} value${remaining.length === 1 ? '' : 's'} remaining`}
      </p>
    </>
  );
}
