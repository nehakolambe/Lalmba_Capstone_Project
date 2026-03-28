import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Questionnaire from './Questionnaire';

test('shows and hides english fluency based on language choice', () => {
  render(<Questionnaire user={{ username: 'alice' }} onSave={jest.fn()} />);

  expect(screen.queryByLabelText(/english fluency/i)).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/language/i), {
    target: { value: 'english' }
  });
  expect(screen.getByLabelText(/english fluency/i)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/language/i), {
    target: { value: 'kiswahili' }
  });
  expect(screen.queryByLabelText(/english fluency/i)).not.toBeInTheDocument();
});

test('submits questionnaire values through onSave', async () => {
  const onSave = jest.fn(() => Promise.resolve());
  render(<Questionnaire user={{ username: 'alice' }} onSave={onSave} />);

  fireEvent.change(screen.getByLabelText(/age group/i), { target: { value: 'teen' } });
  fireEvent.change(screen.getByLabelText(/education level/i), { target: { value: 'class_8' } });
  fireEvent.change(screen.getByLabelText(/language/i), { target: { value: 'english' } });
  fireEvent.change(screen.getByLabelText(/english fluency/i), {
    target: { value: 'beginner' }
  });
  fireEvent.change(screen.getByLabelText(/computer literacy/i), {
    target: { value: 'intermediate' }
  });
  fireEvent.click(screen.getByRole('button', { name: /continue to chat/i }));

  await waitFor(() => expect(onSave).toHaveBeenCalledWith({
    age_group: 'teen',
    education_level: 'class_8',
    preferred_language: 'english',
    english_fluency: 'beginner',
    computer_literacy: 'intermediate'
  }));
});
