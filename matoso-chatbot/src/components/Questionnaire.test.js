import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Questionnaire from './Questionnaire';

test('shows and hides english fluency based on language choice', () => {
  render(<Questionnaire user={{ username: 'alice' }} onSave={jest.fn()} />);

  expect(screen.queryByLabelText(/english understanding/i)).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/language \(lugha\)/i), {
    target: { value: 'english' }
  });
  expect(screen.getByLabelText(/english understanding \(uelewa wa kiingereza\)/i)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/language \(lugha\)/i), {
    target: { value: 'kiswahili' }
  });
  expect(screen.queryByLabelText(/english understanding/i)).not.toBeInTheDocument();
});

test('submits questionnaire values through onSave', async () => {
  const onSave = jest.fn(() => Promise.resolve());
  render(<Questionnaire user={{ username: 'alice' }} onSave={onSave} />);

  fireEvent.change(screen.getByLabelText(/age group \(kikundi cha umri\)/i), { target: { value: 'teen' } });
  fireEvent.change(screen.getByLabelText(/education level \(kiwango cha elimu\)/i), { target: { value: 'class_8' } });
  fireEvent.change(screen.getByLabelText(/language \(lugha\)/i), { target: { value: 'english' } });
  fireEvent.change(screen.getByLabelText(/english understanding \(uelewa wa kiingereza\)/i), {
    target: { value: 'need_help' }
  });
  fireEvent.change(screen.getByLabelText(/computer use \(matumizi ya kompyuta\)/i), {
    target: { value: 'can_do_some' }
  });
  fireEvent.click(screen.getByRole('button', { name: /continue to chat \(endelea kwenye mazungumzo\)/i }));

  await waitFor(() => expect(onSave).toHaveBeenCalledWith({
    age_group: 'teen',
    education_level: 'class_8',
    preferred_language: 'english',
    english_fluency: 'need_help',
    computer_literacy: 'can_do_some'
  }));
});

test('renders bilingual questionnaire copy and simple answer labels', () => {
  render(<Questionnaire user={{ full_name: 'Asha' }} onSave={jest.fn()} />);

  expect(screen.getByRole('heading', { name: /tell us about yourself \(tuambie kukuhusu\)/i })).toBeInTheDocument();
  expect(
    screen.getByText(
      /welcome asha\. please complete your profile before chatting\. \(karibu asha\. tafadhali kamilisha wasifu wako kabla ya kuanza kuzungumza\.\)/i
    )
  ).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /need help \(nahitaji msaada\)/i })).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /can do well \(naweza kufanya vizuri\)/i })).toBeInTheDocument();
});

test('normalizes legacy saved values into the new simple options', () => {
  render(
    <Questionnaire
      user={{ username: 'alice' }}
      initialProfile={{
        age_group: 'teen',
        education_level: 'class_8',
        preferred_language: 'english',
        english_fluency: 'beginner',
        computer_literacy: 'advanced'
      }}
      onSave={jest.fn()}
    />
  );

  expect(screen.getByLabelText(/english understanding \(uelewa wa kiingereza\)/i)).toHaveValue('need_help');
  expect(screen.getByLabelText(/computer use \(matumizi ya kompyuta\)/i)).toHaveValue('can_do_well');
});
