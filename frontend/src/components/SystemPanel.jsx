import React, { useState, useEffect } from 'react';

/**
 * SystemPanel — the System's voice as a bordered magical interface.
 *
 * Modelled on the provided System UI kit: ornate corner filigree, a crowned
 * icon, rules above and below a letterspaced title, and body copy wrapped in
 * brackets with one highlighted keyword.
 *
 * This is deliberately the ONE place the parchment aesthetic breaks. The
 * System is not part of the handcrafted world — it is something overlaid on
 * it — so its panels are dark, glowing and machine-precise while everything
 * around them is paper and ink.
 *
 * Props:
 *   variant:    which panel style (alarm, system, skill_learned, ...)
 *   lines:      [title, ...body]
 *   onComplete: advance past the panel
 */

// Icon + accent per variant, matching the reference sheet.
const VARIANTS = {
  alarm:          { icon: '!',  label: 'ALARM' },
  system:         { icon: '⚙',  label: 'SYSTEM' },
  notification:   { icon: '🔔', label: 'NOTIFICATION' },
  skill_learned:  { icon: '📖', label: 'SKILL LEARNED' },
  status:         { icon: '♥',  label: 'STATUS' },
  warning:        { icon: '⚠',  label: 'WARNING' },
  item_obtained:  { icon: '🧰', label: 'ITEM OBTAINED' },
  level_up:       { icon: '↑',  label: 'LEVEL UP' },
  arrival:        { icon: '⛩',  label: 'ARRIVAL' },
};

export default function SystemPanel({ variant = 'system', lines = [], onComplete }) {
  const meta = VARIANTS[variant] || VARIANTS.system;
  const [title, ...body] = lines;
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setEntered(true), 30);
    return () => clearTimeout(t);
  }, []);

  // Enter or Space should dismiss, same as the dialogue box.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onComplete?.();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onComplete]);

  return (
    <div className="system-panel-stage">
      <div
        className={`system-panel variant-${variant} ${entered ? 'is-entered' : ''}`}
        role="status"
      >
        <span className="system-corner tl" aria-hidden="true" />
        <span className="system-corner tr" aria-hidden="true" />
        <span className="system-corner bl" aria-hidden="true" />
        <span className="system-corner br" aria-hidden="true" />

        <div className="system-crest" aria-hidden="true">{meta.icon}</div>

        <div className="system-title">{title || meta.label}</div>

        <div className="system-body">
          {body.map((line, i) => (
            <p key={i} className="system-line">[{line}]</p>
          ))}
        </div>

        <span className="system-flourish" aria-hidden="true">◆</span>
      </div>

      <button className="btn btn-ghost system-dismiss" onClick={onComplete}>
        Continue →
      </button>
    </div>
  );
}
