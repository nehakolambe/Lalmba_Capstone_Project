import React, { useEffect, useState } from 'react';
import logo from '../assets/logo.png';

const AGE_GROUP_OPTIONS = [
  { value: 'child', label: 'Child' },
  { value: 'teen', label: 'Teen' },
  { value: 'adult', label: 'Adult' }
];

const EDUCATION_LEVEL_OPTIONS = [
  { value: 'class_1', label: 'Class 1' },
  { value: 'class_2', label: 'Class 2' },
  { value: 'class_3', label: 'Class 3' },
  { value: 'class_4', label: 'Class 4' },
  { value: 'class_5', label: 'Class 5' },
  { value: 'class_6', label: 'Class 6' },
  { value: 'class_7', label: 'Class 7' },
  { value: 'class_8', label: 'Class 8' },
  { value: 'class_9', label: 'Class 9' },
  { value: 'class_10', label: 'Class 10' },
  { value: 'high_school', label: 'High School' },
  { value: 'college', label: 'College' },
  { value: 'adult', label: 'Adult' }
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English' },
  { value: 'kiswahili', label: 'Kiswahili' }
];

const SKILL_OPTIONS = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' }
];

function Questionnaire({ user, initialProfile, onSave, onBack, isEditing = false }) {
  const [form, setForm] = useState({
    age_group: '',
    education_level: '',
    preferred_language: '',
    english_fluency: '',
    computer_literacy: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setForm({
      age_group: initialProfile?.age_group || '',
      education_level: initialProfile?.education_level || '',
      preferred_language: initialProfile?.preferred_language || '',
      english_fluency: initialProfile?.english_fluency || '',
      computer_literacy: initialProfile?.computer_literacy || ''
    });
  }, [initialProfile]);

  function handleChange(field, value) {
    setForm(prev => ({
      ...prev,
      [field]: value,
      ...(field === 'preferred_language' && value !== 'english'
        ? { english_fluency: '' }
        : {})
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError('');

    try {
      const payload = {
        ...form,
        english_fluency: form.preferred_language === 'english' ? form.english_fluency : null
      };
      await onSave(payload);
    } catch (err) {
      const details = err?.payload?.details;
      const detailText =
        details && typeof details === 'object'
          ? Object.values(details).filter(Boolean).join(' ')
          : '';
      setError(detailText || err?.message || 'Unable to save your questionnaire right now.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-form questionnaire-form">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="questionnaire-back"
          aria-label="Go back"
        >
          ←
        </button>
      )}

      <div className="login-logo">
        <img src={logo} alt="Matoso Logo" />
      </div>

      <h2>{isEditing ? 'Update your questionnaire' : 'Tell us about yourself'}</h2>
      <p className="questionnaire-intro">
        {isEditing
          ? 'Update your learning profile so Mama Akinyi can keep helping at the right level.'
          : `Welcome ${user?.full_name || user?.username || ''}. Please complete your profile before chatting.`}
      </p>

      <label>
        Age group:
        <select
          value={form.age_group}
          onChange={event => handleChange('age_group', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select age group</option>
          {AGE_GROUP_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      <label>
        Education level:
        <select
          value={form.education_level}
          onChange={event => handleChange('education_level', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select education level</option>
          {EDUCATION_LEVEL_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      <label>
        Language:
        <select
          value={form.preferred_language}
          onChange={event => handleChange('preferred_language', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select language</option>
          {LANGUAGE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      {form.preferred_language === 'english' && (
        <label>
          English fluency:
          <select
            value={form.english_fluency}
            onChange={event => handleChange('english_fluency', event.target.value)}
            disabled={submitting}
            required
          >
            <option value="">Select English fluency</option>
            {SKILL_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      )}

      <label>
        Computer literacy:
        <select
          value={form.computer_literacy}
          onChange={event => handleChange('computer_literacy', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select computer literacy</option>
          {SKILL_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      {error && <p className="login-error">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? 'Saving...' : isEditing ? 'Save changes' : 'Continue to chat'}
      </button>
    </form>
  );
}

export default Questionnaire;
