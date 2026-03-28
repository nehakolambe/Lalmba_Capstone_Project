import React, { useEffect, useState } from 'react';
import logo from '../assets/logo.png';

const LEGACY_SKILL_VALUE_MAP = {
  beginner: 'need_help',
  intermediate: 'can_do_some',
  advanced: 'can_do_well'
};

const AGE_GROUP_OPTIONS = [
  { value: 'child', label: 'Child (Mtoto)' },
  { value: 'teen', label: 'Teen (Kijana)' },
  { value: 'adult', label: 'Adult (Mtu mzima)' }
];

const EDUCATION_LEVEL_OPTIONS = [
  { value: 'class_1', label: 'Class 1 (Darasa la 1)' },
  { value: 'class_2', label: 'Class 2 (Darasa la 2)' },
  { value: 'class_3', label: 'Class 3 (Darasa la 3)' },
  { value: 'class_4', label: 'Class 4 (Darasa la 4)' },
  { value: 'class_5', label: 'Class 5 (Darasa la 5)' },
  { value: 'class_6', label: 'Class 6 (Darasa la 6)' },
  { value: 'class_7', label: 'Class 7 (Darasa la 7)' },
  { value: 'class_8', label: 'Class 8 (Darasa la 8)' },
  { value: 'class_9', label: 'Class 9 (Darasa la 9)' },
  { value: 'class_10', label: 'Class 10 (Darasa la 10)' },
  { value: 'high_school', label: 'High School (Sekondari)' },
  { value: 'college', label: 'College (Chuo)' },
  { value: 'adult', label: 'Adult learning (Elimu ya watu wazima)' }
];

const LANGUAGE_OPTIONS = [
  { value: 'english', label: 'English (Kiingereza)' },
  { value: 'kiswahili', label: 'Kiswahili (Kiswahili)' }
];

const SKILL_OPTIONS = [
  { value: 'need_help', label: 'Need help (Nahitaji msaada)' },
  { value: 'can_do_some', label: 'Can do some (Naweza kufanya kidogo)' },
  { value: 'can_do_well', label: 'Can do well (Naweza kufanya vizuri)' }
];

function normalizeSkillValue(value) {
  return LEGACY_SKILL_VALUE_MAP[value] || value || '';
}

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
      english_fluency: normalizeSkillValue(initialProfile?.english_fluency),
      computer_literacy: normalizeSkillValue(initialProfile?.computer_literacy)
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
      setError(
        detailText ||
          err?.message ||
          'Unable to save your questionnaire right now. (Haiwezekani kuhifadhi dodoso lako sasa hivi.)'
      );
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
          aria-label="Go back (Rudi nyuma)"
        >
          ←
        </button>
      )}

      <div className="login-logo">
        <img src={logo} alt="Matoso Logo" />
      </div>

      <h2>{isEditing ? 'Update your questionnaire (Sasisha dodoso lako)' : 'Tell us about yourself (Tuambie kukuhusu)'}</h2>
      <p className="questionnaire-intro">
        {isEditing
          ? 'Update your learning profile so Mama Akinyi can keep helping at the right level. (Sasisha wasifu wako wa kujifunza ili Mama Akinyi aendelee kukusaidia kwa kiwango kinachokufaa.)'
          : `Welcome ${user?.full_name || user?.username || ''}. Please complete your profile before chatting. (Karibu ${user?.full_name || user?.username || ''}. Tafadhali kamilisha wasifu wako kabla ya kuanza kuzungumza.)`}
      </p>

      <label>
        Age group (Kikundi cha umri):
        <select
          value={form.age_group}
          onChange={event => handleChange('age_group', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select age group (Chagua kikundi cha umri)</option>
          {AGE_GROUP_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      <label>
        Education level (Kiwango cha elimu):
        <select
          value={form.education_level}
          onChange={event => handleChange('education_level', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select education level (Chagua kiwango cha elimu)</option>
          {EDUCATION_LEVEL_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      <label>
        Language (Lugha):
        <select
          value={form.preferred_language}
          onChange={event => handleChange('preferred_language', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select language (Chagua lugha)</option>
          {LANGUAGE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      {form.preferred_language === 'english' && (
        <label>
          English understanding (Uelewa wa Kiingereza):
          <select
            value={form.english_fluency}
            onChange={event => handleChange('english_fluency', event.target.value)}
            disabled={submitting}
            required
          >
            <option value="">Select English understanding (Chagua uelewa wa Kiingereza)</option>
            {SKILL_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      )}

      <label>
        Computer use (Matumizi ya kompyuta):
        <select
          value={form.computer_literacy}
          onChange={event => handleChange('computer_literacy', event.target.value)}
          disabled={submitting}
          required
        >
          <option value="">Select computer use (Chagua matumizi ya kompyuta)</option>
          {SKILL_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      {error && <p className="login-error">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting
          ? 'Saving... (Inahifadhi...)'
          : isEditing
            ? 'Save changes (Hifadhi mabadiliko)'
            : 'Continue to chat (Endelea kwenye mazungumzo)'}
      </button>
    </form>
  );
}

export default Questionnaire;
