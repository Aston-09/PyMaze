import React, { useState, useEffect } from 'react';

/**
 * RevealChests — click each chest to open it and see the value it holds.
 *
 * Teaches the shape of a variable physically: a name on the lid, one value
 * inside. Solved once every chest has been opened.
 */
export default function RevealChests({ config, onSolved }) {
  const chests = config.chests || [];
  const [opened, setOpened] = useState(() => new Set());

  const allOpen = chests.length > 0 && opened.size === chests.length;

  useEffect(() => {
    if (allOpen) onSolved?.();
  }, [allOpen, onSolved]);

  const open = (name) => setOpened((prev) => new Set(prev).add(name));

  return (
    <>
      <div className="chest-grid">
        {chests.map((chest) => {
          const isOpen = opened.has(chest.name);
          return (
            <button
              key={chest.name}
              className={`chest ${isOpen ? 'is-open' : ''}`}
              onClick={() => open(chest.name)}
              disabled={isOpen}
              aria-label={isOpen ? `${chest.name} holds ${chest.value}` : `Open the chest labelled ${chest.name}`}
            >
              <div className="chest-lid">{chest.name}</div>
              <div className="chest-body">
                {isOpen ? (
                  <>
                    <span className="chest-value">{chest.value}</span>
                    {chest.caption && <span className="chest-caption">{chest.caption}</span>}
                  </>
                ) : (
                  <span className="chest-sealed">— sealed —</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <p className="interaction-progress">
        {allOpen ? 'Every chest lies open' : `${opened.size} of ${chests.length} opened`}
      </p>
    </>
  );
}
