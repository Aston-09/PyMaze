import React, { useState, useEffect } from 'react';
import useAdvanceKey from '../../utils/useAdvanceKey';

/** A, B, C… — the label that makes an option look like an option. */
const KEYS = 'ABCDEFGH';

/**
 * PredictOutput — read a snippet, predict what it prints.
 *
 * The workhorse of the chapter's conceptual beats: the quote boundary, what
 * print() actually shows, and what input() hands back. A wrong guess still
 * reveals the explanation and lets the learner move on — the point is the
 * insight, not the score.
 *
 * A round may carry its own `question`; without one the card asks the
 * standard "What does this print?", so the code, the question and the
 * answers always read as three separate things rather than one wall.
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

  // Enter moves to the next round once an answer is in. Handing over to the
  // stage's own Continue key the moment this widget is done keeps one press
  // from advancing two beats.
  useAdvanceKey(next, answered && !finished);

  if (!round) return null;

  return (
    <div className="predict-card">
      <pre className="predict-code">{round.code}</pre>

      <p className="predict-ask">{round.question || 'What does this print?'}</p>

      <div className="predict-options" role="group" aria-label="Answer options">
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
              <span className="predict-key" aria-hidden="true">{KEYS[i] || '•'}</span>
              <span className="predict-answer">{opt}</span>
            </button>
          );
        })}
      </div>

      {answered && round.explain && (
        <p className={`predict-explain ${choice === round.answer ? 'is-right' : 'is-wrong'}`}>
          {round.explain}
        </p>
      )}

      {answered && !finished && (
        <div className="predict-next">
          <button className="btn btn-primary" onClick={next}>
            {isLast ? 'Done →' : 'Next question →'}
          </button>
        </div>
      )}

      <p className="interaction-progress">
        {finished ? 'All predictions made' : `Question ${index + 1} of ${rounds.length}`}
      </p>
    </div>
  );
}
