import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login form heading after session check', async () => {
  render(<App />);
  const heading = await screen.findByRole('heading', {
    name: /welcome to matoso help desk/i
  });
  expect(heading).toBeInTheDocument();
});
