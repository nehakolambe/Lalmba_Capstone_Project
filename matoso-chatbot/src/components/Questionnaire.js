import React, { useEffect, useMemo, useState } from 'react';

const AGE_OPTIONS = ['12-18', '19-30', '31-45', '46+', 'Prefer not to say'];
const LANGUAGE_OPTIONS = ['English', 'Kiswahili', 'Other'];
const LEVEL_OPTIONS = ['Low', 'Medium', 'High'];
const HOURS_OPTIONS = ['0-2', '3-5', '6-10', '11-15', '16+'];
const GOAL_OPTIONS = [
  'Start a small business',
  'Improve computer basics',
  'Learn office tools',
  'Job readiness',
  'School support',
  'Other'
];
const TOPIC_OPTIONS = [
  'Documents & typing',
  'Spreadsheets',
  'Internet & email',
  'Photos & media',
  'Budgeting',
  'Entrepreneurship',
  'Other'
];

function normalizeAnswers(raw, user) {
  const safe = raw && typeof raw === 'object' ? raw : {};
  return {
    name: safe.name || user?.full_name || user?.username || '',
    age_range: safe.age_range || '',
    language_preference: safe.language_preference || '',
    literacy_level: safe.literacy_level || '',
    typing_comfort: safe.typing_comfort || '',
    learning_goals: Array.isArray(safe.learning_goals) ? safe.learning_goals : [],
    hours_per_week: safe.hours_per_week || '',
    topics_interest: Array.isArray(safe.topics_interest) ? safe.topics_interest : [],
    prior_experience: safe.prior_experience || '',
    help_today: safe.help_today || '',
    consent: Boolean(safe.consent)
  };
}

function Questionnaire({ user, initialAnswers, onSubmit, onCancel, submitting, error }) {
  const [answers, setAnswers] = useState(() => normalizeAnswers(initialAnswers, user));
  const [touched, setTouched] = useState({});

  useEffect(() => {
    setAnswers(normalizeAnswers(initialAnswers, user));
  }, [initialAnswers, user]);

  const validation = useMemo(() => {
    const errors = {};
    if (!answers.age_range) errors.age_range = 'Select an age range.';
    if (!answers.language_preference) errors.language_preference = 'Select a language.';
    if (!answers.literacy_level) errors.literacy_level = 'Select a literacy level.';
    if (!answers.typing_comfort) errors.typing_comfort = 'Select a typing comfort level.';
    if (!answers.learning_goals.length) errors.learning_goals = 'Select at least one goal.';
    if (!answers.hours_per_week) errors.hours_per_week = 'Select available hours.';
    if (!answers.topics_interest.length) errors.topics_interest = 'Select at least one topic.';
    if (!answers.prior_experience.trim()) errors.prior_experience = 'Provide a short note.';
    if (!answers.help_today.trim()) errors.help_today = 'Tell us what you need help with.';
    return errors;
  }, [answers]);

  const isValid = Object.keys(validation).length === 0;

  function handleChange(name, value) {
    setAnswers(prev => ({ ...prev, [name]: value }));
  }

  function handleCheckboxList(name, value) {
    setAnswers(prev => {
      const current = new Set(prev[name] || []);
      if (current.has(value)) {
        current.delete(value);
      } else {
        current.add(value);
      }
      return { ...prev, [name]: Array.from(current) };
    });
  }

  function markTouched(name) {
    setTouched(prev => ({ ...prev, [name]: true }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    const allTouched = {};
    Object.keys(validation).forEach(key => {
      allTouched[key] = true;
    });
    setTouched(prev => ({ ...prev, ...allTouched }));
    if (!isValid) return;
    if (typeof onSubmit === 'function') {
      onSubmit(answers);
    }
  }

  const displayName = (user?.full_name || user?.username || 'User').trim() || 'User';

  return (
    <div className="questionnaire-shell">
      <form className="questionnaire-card" onSubmit={handleSubmit}>
        <h2>Welcome, {displayName}</h2>
        <p className="questionnaire-subtitle">
          Please answer a few quick questions so we can personalize your experience.
        </p>

        <div className="questionnaire-grid">
          <label className="field">
            Name
            <input value={answers.name} readOnly />
          </label>

          <label className="field">
            Age range *
            <select
              value={answers.age_range}
              onChange={e => handleChange('age_range', e.target.value)}
              onBlur={() => markTouched('age_range')}
            >
              <option value="">Select...</option>
              {AGE_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {touched.age_range && validation.age_range && (
              <span className="field-error">{validation.age_range}</span>
            )}
          </label>

          <label className="field">
            Preferred language *
            <select
              value={answers.language_preference}
              onChange={e => handleChange('language_preference', e.target.value)}
              onBlur={() => markTouched('language_preference')}
            >
              <option value="">Select...</option>
              {LANGUAGE_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {touched.language_preference && validation.language_preference && (
              <span className="field-error">{validation.language_preference}</span>
            )}
          </label>

          <label className="field">
            Literacy level *
            <select
              value={answers.literacy_level}
              onChange={e => handleChange('literacy_level', e.target.value)}
              onBlur={() => markTouched('literacy_level')}
            >
              <option value="">Select...</option>
              {LEVEL_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {touched.literacy_level && validation.literacy_level && (
              <span className="field-error">{validation.literacy_level}</span>
            )}
          </label>

          <label className="field">
            Typing comfort *
            <select
              value={answers.typing_comfort}
              onChange={e => handleChange('typing_comfort', e.target.value)}
              onBlur={() => markTouched('typing_comfort')}
            >
              <option value="">Select...</option>
              {LEVEL_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {touched.typing_comfort && validation.typing_comfort && (
              <span className="field-error">{validation.typing_comfort}</span>
            )}
          </label>

          <div className="field field-full">
            <span>Learning goals *</span>
            <div className="field-options">
              {GOAL_OPTIONS.map(option => (
                <label key={option} className="checkbox-option">
                  <input
                    type="checkbox"
                    checked={answers.learning_goals.includes(option)}
                    onChange={() => handleCheckboxList('learning_goals', option)}
                    onBlur={() => markTouched('learning_goals')}
                  />
                  {option}
                </label>
              ))}
            </div>
            {touched.learning_goals && validation.learning_goals && (
              <span className="field-error">{validation.learning_goals}</span>
            )}
          </div>

          <label className="field">
            Hours per week *
            <select
              value={answers.hours_per_week}
              onChange={e => handleChange('hours_per_week', e.target.value)}
              onBlur={() => markTouched('hours_per_week')}
            >
              <option value="">Select...</option>
              {HOURS_OPTIONS.map(option => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <span className="field-help">How much time you can spend learning each week.</span>
            {touched.hours_per_week && validation.hours_per_week && (
              <span className="field-error">{validation.hours_per_week}</span>
            )}
          </label>

          <div className="field field-full">
            <span>Topics of interest *</span>
            <div className="field-options">
              {TOPIC_OPTIONS.map(option => (
                <label key={option} className="checkbox-option">
                  <input
                    type="checkbox"
                    checked={answers.topics_interest.includes(option)}
                    onChange={() => handleCheckboxList('topics_interest', option)}
                    onBlur={() => markTouched('topics_interest')}
                  />
                  {option}
                </label>
              ))}
            </div>
            {touched.topics_interest && validation.topics_interest && (
              <span className="field-error">{validation.topics_interest}</span>
            )}
          </div>

          <label className="field field-full">
            Prior computer experience *
            <input
              value={answers.prior_experience}
              onChange={e => handleChange('prior_experience', e.target.value)}
              onBlur={() => markTouched('prior_experience')}
              placeholder="e.g., basics with typing and internet"
            />
            {touched.prior_experience && validation.prior_experience && (
              <span className="field-error">{validation.prior_experience}</span>
            )}
          </label>

          <label className="field field-full">
            What do you want help with today? *
            <textarea
              rows={3}
              value={answers.help_today}
              onChange={e => handleChange('help_today', e.target.value)}
              onBlur={() => markTouched('help_today')}
            />
            {touched.help_today && validation.help_today && (
              <span className="field-error">{validation.help_today}</span>
            )}
          </label>

          <label className="field field-full checkbox-option">
            <input
              type="checkbox"
              checked={answers.consent}
              onChange={e => handleChange('consent', e.target.checked)}
            />
            I understand this information helps personalize my learning experience.
          </label>
        </div>

        {error && <p className="questionnaire-error">{error}</p>}

        <div className="questionnaire-actions">
          {typeof onCancel === 'function' && (
            <button type="button" className="ghost-btn" onClick={onCancel} disabled={submitting}>
              Back
            </button>
          )}
          <button type="submit" className="home-btn primary" disabled={submitting || !isValid}>
            {submitting ? 'Saving...' : 'Submit'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Questionnaire;
