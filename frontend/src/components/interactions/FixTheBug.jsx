import React, { useState, useEffect } from 'react';

/**
 * FixTheBug — find the broken line, then choose the repair.
 *
 * Two acts, because debugging is two skills. First locate the fault by
 * clicking the offending line; then pick what it should have said. Locating
 * is the half a multiple-choice quiz never trains, and it is the half that
 * transfers to the learner's own code.
 *
 * A wrong line is not punished — it says why that line is fine, which teaches
 * the same lesson from the other side.
 *
 * config:
 *   code:      array of source lines
 *   bug_line:  0-based index of the broken one
 *   symptom:   what goes wrong when this runs
 *   line_hints: { "<index>": "why this line is innocent" }
 *   fixes:     [{ text, correct, why }]
 *   success:   closing line
 */
export default function FixTheBug({ config, onSolved }) {
  const code = config.code || [];
  const fixes = config.fixes || [];
  const hints = config.line_hints || {};

  const [found, setFound] = useState(false);
  const [wrongLine, setWrongLine] = useState(null);
  const [picked, setPicked] = useState(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) onSolved?.();
  }, [done, onSolved]);

  const clickLine = (i) => {
    if (found) return;
    if (i === config.bug_line) {
      setFound(true);
      setWrongLine(null);
    } else {
      setWrongLine(i);
    }
  };

  const pick = (i) => {
    if (picked !== null) return;
    setPicked(i);
    if (fixes[i]?.correct) setDone(true);
  };

  return (
    <div className="predict-card">
      {config.symptom && (
        <p className="interaction-prompt">
          <strong>It runs, but:</strong> {config.symptom}
        </p>
      )}

      <pre className="predict-code">
        {code.map((line, i) => {
          let state = '';
          if (found && i === config.bug_line) state = ' is-bug';
          else if (wrongLine === i) state = ' is-innocent';
          return (
            <div
              key={i}
              className={`trace-line is-clickable${state}`}
              onClick={() => clickLine(i)}
              role="button"
              tabIndex={found ? -1 : 0}
              onKeyDown={(e) => e.key === 'Enter' && clickLine(i)}
              aria-label={`Line ${i + 1}: ${line}`}
            >
              {line || ' '}
            </div>
          );
        })}
      </pre>

      {!found && (
        <p className="interaction-progress">
          {wrongLine !== null
            ? hints[String(wrongLine)] || 'That line is doing its job. Look again.'
            : 'Click the line that causes it.'}
        </p>
      )}

      {found && (
        <>
          <p className="predict-explain is-right">Found it. Now — what should it say?</p>
          <div className="predict-options">
            {fixes.map((fix, i) => {
              let state = '';
              if (picked !== null && fix.correct) state = 'is-correct';
              else if (picked === i) state = 'is-wrong';
              return (
                <button
                  key={i}
                  className={`predict-option ${state}`}
                  onClick={() => pick(i)}
                  disabled={picked !== null}
                >
                  {fix.text}
                </button>
              );
            })}
          </div>
          {picked !== null && fixes[picked]?.why && (
            <p className="predict-explain">{fixes[picked].why}</p>
          )}
          {picked !== null && !fixes[picked]?.correct && (
            <button
              className="btn btn-ghost"
              onClick={() => setPicked(null)}
            >
              Try another fix
            </button>
          )}
        </>
      )}

      {done && config.success && (
        <p className="interaction-resolve">{config.success}</p>
      )}
    </div>
  );
}
