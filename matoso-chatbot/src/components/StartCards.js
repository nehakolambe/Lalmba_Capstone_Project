import React from 'react';

export const START_CARDS = [
  {
    id: 'internet-basics',
    label: 'Internet basics',
    icon: 'WEB',
    prompt: "I'm new to computers. Teach me internet basics and online safety step-by-step using very simple instructions."
  },
  {
    id: 'english',
    label: 'Learn English',
    icon: '📖',
    prompt: 'Teach me English with short, simple sentences. Start with greetings.'
  },
  {
    id: 'math',
    label: 'Math practice',
    icon: '➕',
    prompt: 'Give me easy math practice, one question at a time.'
  },
  {
    id: 'business',
    label: 'Small business',
    icon: '🧺',
    prompt: 'Give me simple advice for a small business. Ask me what I sell.'
  },
  {
    id: 'farming',
    label: 'Farming',
    icon: '🌱',
    prompt: 'Give me simple farming tips. Ask me what I grow.'
  },
  {
    id: 'health',
    label: 'Health',
    icon: '❤️',
    prompt: 'Give me simple health tips. Ask me my question first.'
  },
  {
    id: 'computer-basics',
    label: 'Computer basics',
    icon: '💻',
    prompt: "I'm new to computers. Teach me the basics step-by-step."
  }
];

function StartCards({ onSelect, title = '', subtitle = '' }) {
  const showHeader = Boolean(title || subtitle);
  return (
    <section className="start-cards">
      {showHeader && (
        <div className="start-cards-header">
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      )}
      <div className="start-cards-grid">
        {START_CARDS.map(card => (
          <button
            key={card.id}
            type="button"
            className="start-card"
            onClick={() => onSelect(card)}
          >
            <span className="start-card-icon" aria-hidden="true">
              {card.icon}
            </span>
            <span className="start-card-label">{card.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default StartCards;
