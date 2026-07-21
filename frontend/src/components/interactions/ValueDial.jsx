import React, { useState, useEffect } from 'react';

/**
 * ValueDial — reassign a variable and watch the old value be forgotten.
 *
 * The single idea this beat exists to land: assignment replaces. The previous
 * value is shown struck through only until the new one is committed, then it
 * is gone — because that is exactly what Python does to it.
 */
export default function ValueDial({ config, onSolved }) {
  const { variable, initial, target, min = 0, max = 99, before_caption, success } = config;

  const [value, setValue] = useState(initial);
  const [committed, setCommitted] = useState(false);

  const matches = value === target;

  useEffect(() => {
    if (committed) onSolved?.();
  }, [committed, onSolved]);

  return (
    <>
      <div className="dial-panel">
        {before_caption && !committed && (
          <span className="chest-caption">{before_caption}</span>
        )}

        <div className="dial-statement">
          {variable} ={' '}
          {committed ? (
            <>
              <span className="dial-old">{initial}</span>
              <span className="dial-new">{value}</span>
            </>
          ) : (
            <span>{value}</span>
          )}
        </div>

        {!committed && (
          <>
            <div className="dial-controls">
              <button
                className="dial-btn"
                onClick={() => setValue((v) => Math.max(min, v - 1))}
                disabled={value <= min}
                aria-label="Decrease value"
              >−</button>
              <span className="dial-readout">{value}</span>
              <button
                className="dial-btn"
                onClick={() => setValue((v) => Math.min(max, v + 1))}
                disabled={value >= max}
                aria-label="Increase value"
              >+</button>
            </div>

            <button
              className="btn btn-primary"
              onClick={() => setCommitted(true)}
              disabled={!matches}
            >
              {matches ? 'Seal the chest' : `Set ${variable} to ${target}`}
            </button>
          </>
        )}
      </div>

      {committed && success && <p className="interaction-resolve">{success}</p>}
    </>
  );
}
