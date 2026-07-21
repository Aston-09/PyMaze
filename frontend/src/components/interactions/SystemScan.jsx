import React, { useState, useEffect } from 'react';

/**
 * SystemScan — a recovered record the learner reads line by line.
 *
 * Used both to show the player their own character sheet and to reveal the
 * type of each value. Solved once every line has been touched.
 */
export default function SystemScan({ config, onSolved }) {
  const lines = config.lines || [];
  const [read, setRead] = useState(() => new Set());

  const allRead = lines.length > 0 && read.size === lines.length;

  useEffect(() => {
    if (allRead) onSolved?.();
  }, [allRead, onSolved]);

  return (
    <>
      <div className="scan-sheet">
        {config.scan_label && <div className="scan-label">{config.scan_label}</div>}

        {lines.map((line, i) => {
          const isRead = read.has(i);
          return (
            <button
              key={i}
              className={`scan-line ${isRead ? 'is-read' : ''}`}
              onClick={() => setRead((prev) => new Set(prev).add(i))}
              aria-expanded={isRead}
            >
              <span className="scan-code">{line.code}</span>
              {isRead && line.note && (
                <span className={`scan-note ${line.accent ? `accent-${line.accent}` : ''}`}>
                  {line.note}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <p className="interaction-progress">
        {allRead ? 'Record fully read' : `${read.size} of ${lines.length} lines read`}
      </p>
    </>
  );
}
