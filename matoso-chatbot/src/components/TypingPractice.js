import React, { useMemo, useState } from 'react';

function TypingPractice({ open, displayName, onClose, onSendProgress }) {
  const steps = useMemo(() => {
    const safeName = (displayName || 'Your Name').trim() || 'Your Name';
    return [
      {
        id: 'space',
        title: 'Step 1',
        instruction: 'Press space bar',
        expected: ' ',
        hint: 'Press one space.'
      },
      {
        id: 'name',
        title: 'Step 2',
        instruction: 'Type your name',
        expected: safeName,
        hint: `Example: ${safeName}`
      },
      {
        id: 'hello',
        title: 'Step 3',
        instruction: 'Type: hello',
        expected: 'hello',
        hint: 'Type the word: hello'
      }
    ];
  }, [displayName]);

  const [stepIndex, setStepIndex] = useState(0);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('');

  if (!open) return null;

  const step = steps[stepIndex];
  const normalize = value => {
    if (step.id === 'space') {
      if (value.length > 0 && value.trim() === '') {
        return ' ';
      }
      return value;
    }
    return value.trim().toLowerCase();
  };
  const expected = normalize(step.expected);
  const actual = normalize(input);
  const isCorrect = actual === expected;

  function handleCheck() {
    if (isCorrect) {
      setStatus('success');
    } else {
      setStatus('error');
    }
  }

  function handleNext() {
    const nextIndex = Math.min(stepIndex + 1, steps.length - 1);
    setStepIndex(nextIndex);
    setInput('');
    setStatus('');
  }

  function handleRestart() {
    setStepIndex(0);
    setInput('');
    setStatus('');
  }

  const isLast = stepIndex === steps.length - 1;
  const stepNumber = stepIndex + 1;

  return (
    <div className="typing-overlay" role="dialog" aria-modal="true">
      <div className="typing-panel">
        <div className="typing-header">
          <div>
            <h3>Typing practice</h3>
            <p>{step.title}</p>
          </div>
          <button type="button" className="ghost-btn typing-close" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="typing-body">
          <div className="typing-instruction">{step.instruction}</div>
          <div className="typing-hint">{step.hint}</div>
          <input
            className="typing-input"
            value={input}
            onChange={e => {
              setInput(e.target.value);
              if (status) setStatus('');
            }}
            placeholder="Type here"
          />
          <div className="typing-actions">
            <button type="button" className="home-btn primary" onClick={handleCheck}>
              Check
            </button>
            <button type="button" className="home-btn" onClick={handleRestart}>
              Start over
            </button>
          </div>
          {status === 'success' && (
            <div className="typing-success">
              ✅ Great job!
              <div className="typing-success-actions">
                <button
                  type="button"
                  className="home-btn primary"
                  onClick={() => onSendProgress(`I finished typing practice step ${stepNumber}.`)}
                >
                  Tell Mama Akinyi I finished step {stepNumber}
                </button>
                {!isLast && (
                  <button type="button" className="home-btn" onClick={handleNext}>
                    Next step
                  </button>
                )}
              </div>
            </div>
          )}
          {status === 'error' && (
            <div className="typing-error">Try again. You can do it.</div>
          )}
          {isLast && status === 'success' && (
            <div className="typing-complete">You finished all steps! 🎉</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TypingPractice;
