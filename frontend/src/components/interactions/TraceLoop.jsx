import React, { useState, useEffect } from 'react';

/**
 * TraceLoop — step through code one line at a time, predicting each change.
 *
 * Where `predict_output` asks for the answer at the end, this asks for the
 * next step, over and over: the learner is the interpreter. A loop that runs
 * four times is four predictions, so the shape of the repetition is felt
 * rather than described.
 *
 * The learner types the value a variable holds after the highlighted line
 * runs. A wrong answer says so and shows the truth — the point is watching
 * state move, not scoring.
 *
 * config:
 *   code:  array of source lines, shown with the active one highlighted
 *   steps: [{ line, variable, value, note }]
 *          `line` is the 0-based index into `code` that is about to run,
 *          `value` what `variable` holds once it has.
 *   success: closing line once every step is traced
 */
export default function TraceLoop({ config, onSolved }) {
  const code = config.code || [];
  const steps = config.steps || [];

  const [index, setIndex] = useState(0);
  const [guess, setGuess] = useState('');
  const [verdict, setVerdict] = useState(null);   // 'right' | 'wrong' | null
  const [done, setDone] = useState(false);

  const step = steps[index];
  const isLast = index >= steps.length - 1;

  useEffect(() => {
    if (done) onSolved?.();
  }, [done, onSolved]);

  if (!step) return null;

  const check = () => {
    if (verdict) return;
    const expected = String(step.value).trim();
    const got = guess.trim();
    // Compare loosely on quotes so "Fire" and Fire both pass — the lesson is
    // the value, not the transcription.
    const norm = (s) => s.replace(/^['"]|['"]$/g, '').toLowerCase();
    setVerdict(norm(got) === norm(expected) ? 'right' : 'wrong');
  };

  const next = () => {
    if (isLast) {
      setDone(true);
    } else {
      setIndex((i) => i + 1);
      setGuess('');
      setVerdict(null);
    }
  };

  // Everything already traced, so the learner can see the history build up.
  const history = steps.slice(0, index);

  return (
    <div className="predict-card">
      <pre className="predict-code">
        {code.map((line, i) => (
          <div
            key={i}
            className={`trace-line${i === step.line ? ' is-active' : ''}`}
          >
            {line || ' '}
          </div>
        ))}
      </pre>

      {history.length > 0 && (
        <div className="trace-history">
          {history.map((h, i) => (
            <span key={i} className="trace-chip">
              {h.variable} = {String(h.value)}
            </span>
          ))}
        </div>
      )}

      <p className="interaction-prompt">
        After the highlighted line runs, what does <code>{step.variable}</code> hold?
      </p>

      <div className="trace-entry">
        <span className="trace-var">{step.variable} =</span>
        <input
          className="trace-input"
          value={guess}
          onChange={(e) => setGuess(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (verdict ? next() : check())}
          disabled={!!verdict}
          aria-label={`Value of ${step.variable} after this line`}
          autoFocus
        />
        {!verdict && (
          <button className="btn btn-primary" onClick={check} disabled={!guess.trim()}>
            Step →
          </button>
        )}
      </div>

      {verdict && (
        <p className={`predict-explain ${verdict === 'right' ? 'is-right' : 'is-wrong'}`}>
          {verdict === 'right'
            ? `Yes — ${step.variable} is now ${step.value}.`
            : `Not quite. ${step.variable} is ${step.value}.`}
          {step.note ? ` ${step.note}` : ''}
        </p>
      )}

      {verdict && !done && (
        <button className="btn btn-ghost" onClick={next}>
          {isLast ? 'Done' : 'Next step →'}
        </button>
      )}

      {done && config.success && (
        <p className="interaction-resolve">{config.success}</p>
      )}

      <p className="interaction-progress">
        {done ? 'Trace complete' : `Step ${index + 1} of ${steps.length}`}
      </p>
    </div>
  );
}
