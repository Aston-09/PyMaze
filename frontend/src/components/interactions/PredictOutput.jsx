import React, { useState, useEffect } from 'react';

/**
 * PredictOutput — read a snippet, predict what it prints.
 *
 * The workhorse of the chapter's conceptual beats: the quote boundary, what
 * print() actually shows, and what input() hands back. A wrong guess still
 * reveals the explanation and lets the learner move on — the point is the
 * insight, not the score.
 */
export default function PredictOutput({ config, onSolved }) {
  const rounds = config.rounds || [];
  const [index, setIndex] = useState(0);
  const [choice, setChoice] = useState(null);
  const [finished, setFinished] = useState(false);

  const round = rounds[index];
  const answered = choice !== null;
  const isLast = index >= rounds.length - 1;

  useEffect(() => {
    if (finished) onSolved?.();
  }, [finished, onSolved]);

  const next = () => {
    if (isLast) {
      setFinished(true);
    } else {
      setIndex((i) => i + 1);
      setChoice(null);
    }
  };

  if (!round) return null;

  return (
    <div className="predict-card">
      <pre className="predict-code">{round.code}</pre>

      <div className="predict-options">
        {(round.options || []).map((opt, i) => {
          let state = '';
          if (answered && i === round.answer) state = 'is-correct';
          else if (answered && i === choice) state = 'is-wrong';

          return (
            <button
              key={i}
              className={`predict-option ${state}`}
              onClick={() => setChoice(i)}
              disabled={answered}
            >
              {opt}
            </button>
          );
        })}
      </div>

      {answered && round.explain && (
        <p className="predict-explain">{round.explain}</p>
      )}

      {answered && !finished && (
        <button className="btn btn-ghost" onClick={next}>
          {isLast ? 'Done' : 'Next →'}
        </button>
      )}

      <p className="interaction-progress">
        {finished ? 'All predictions made' : `Prediction ${index + 1} of ${rounds.length}`}
      </p>
    </div>
  );
}
