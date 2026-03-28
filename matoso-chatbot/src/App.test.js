import { render, screen } from '@testing-library/react';
import * as api from './api';
import App from './App';

jest.mock('./api');

test('renders login form heading after session check', async () => {
  api.fetchSession.mockResolvedValue(null);
  render(<App />);
  const heading = await screen.findByRole('heading', {
    name: /welcome to matoso smart space/i
  });
  expect(heading).toBeInTheDocument();
});

test('routes incomplete session users to the questionnaire', async () => {
  api.fetchSession.mockResolvedValue({
    id: 1,
    username: 'alice',
    full_name: 'Alice',
    profile_complete: false
  });

  render(<App />);

  expect(await screen.findByRole('heading', { name: /tell us about yourself/i })).toBeInTheDocument();
});
