import React, { useState, useEffect } from 'react';

/**
 * BuildStatement — assemble an assignment from fragments.
 *
 * The learner builds `name = value` by placing pieces into labelled slots.
 * Decoy fragments (`==`, a quoted number) carry their own explanation, so a
 * wrong reach teaches the distinction instead of just rejecting it.
 */
export default function BuildStatement({ config, onSolved }) {
  const slots = config.slots || [];
  const fragments = config.fragments || [];
  const labels = config.slot_labels || {};

  const [filled, setFilled] = useState({});   // slot -> fragment id
  const [selected, setSelected] = useState(null);
  const [wrongId, setWrongId] = useState(null);
  const [hint, setHint] = useState(null);

  const done = slots.length > 0 && slots.every((s) => s in filled);

  useEffect(() => {
    if (done) onSolved?.();
  }, [done, onSolved]);

  const usedIds = new Set(Object.values(filled));
  const available = fragments.filter((f) => !usedIds.has(f.id));

  const placeInto = (slot) => {
    if (!selected) return;
    const frag = fragments.find((f) => f.id === selected);
    if (!frag) return;

    if (frag.slot === slot) {
      setFilled((prev) => ({ ...prev, [slot]: frag.id }));
      setSelected(null);
      setHint(null);
    } else {
      setWrongId(frag.id);
      setHint(frag.wrong_hint || 'That piece does not belong there.');
      setTimeout(() => setWrongId(null), 420);
    }
  };

  const textOf = (id) => fragments.find((f) => f.id === id)?.text || '';

  return (
    <>
      <div className="slot-row">
        {slots.map((slot) => (
          <button
            key={slot}
            className={`slot ${slot in filled ? 'is-filled' : ''}`}
            onClick={() => placeInto(slot)}
            disabled={!selected || slot in filled}
          >
            {slot in filled
              ? <span className="slot-value">{textOf(filled[slot])}</span>
              : <span className="slot-label">{labels[slot] || slot}</span>}
          </button>
        ))}
      </div>

      <div className="sort-tray">
        {available.length === 0 ? (
          <span className="chest-caption">All pieces placed.</span>
        ) : (
          available.map((frag) => (
            <button
              key={frag.id}
              className={`token ${selected === frag.id ? 'is-selected' : ''} ${wrongId === frag.id ? 'is-wrong' : ''}`}
              onClick={() => setSelected(selected === frag.id ? null : frag.id)}
              aria-pressed={selected === frag.id}
            >
              {frag.text}
            </button>
          ))
        )}
      </div>

      {hint && !done && <p className="predict-explain">{hint}</p>}
      {done && config.success && <p className="interaction-resolve">{config.success}</p>}
    </>
  );
}
