import React from 'react';

const QUICK_REPLIES = [
  { label: '✅ Yes', value: 'Yes' },
  { label: '❌ No', value: 'No' },
  { label: '🔁 Repeat', value: 'Repeat' },
  { label: '▶️ Next', value: 'Next' }
];

function QuickReplies({ onSelect, hidden, disabled }) {
  if (hidden) return null;
  return (
    <div className="quick-replies" aria-label="Quick replies">
      {QUICK_REPLIES.map(item => (
        <button
          key={item.value}
          type="button"
          className="quick-reply-btn"
          onClick={() => onSelect(item.value)}
          disabled={disabled}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export default QuickReplies;
