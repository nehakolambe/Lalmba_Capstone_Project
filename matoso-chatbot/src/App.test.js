import { render, screen } from '@testing-library/react';
import * as api from './api';
import App from './App';

jest.mock('./api');

test('renders login form heading after session check', async () => {
  api.fetchSession.mockResolvedValue(null);
  render(<App />);
  const heading = await screen.findByRole('heading', {
    name: /welcome to matoso help desk/i
  });
  expect(heading).toBeInTheDocument();
});
