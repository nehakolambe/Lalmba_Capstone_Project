import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Login from './Login';

test('submits login credentials through onLogin', async () => {
  const onLogin = jest.fn(() => Promise.resolve({ success: true }));
  render(<Login onLogin={onLogin} />);

  fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alice' } });
  fireEvent.change(screen.getByLabelText(/^pin:/i), { target: { value: '1234' } });
  fireEvent.click(screen.getByRole('button', { name: /login/i }));

  await waitFor(() => expect(onLogin).toHaveBeenCalledWith('alice', '1234'));
});

test('shows register validation errors returned from handler', async () => {
  const onRegister = jest.fn(() =>
    Promise.resolve({
      success: false,
      message: 'Invalid registration data',
      details: { fullName: 'Full name is required.' }
    })
  );

  render(<Login onLogin={jest.fn()} onRegister={onRegister} />);

  fireEvent.click(screen.getByRole('button', { name: /create one here/i }));
  fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alice' } });
  fireEvent.change(screen.getByLabelText(/choose a pin\/password/i), {
    target: { value: '1234' }
  });
  fireEvent.click(screen.getByRole('button', { name: /create account/i }));

  expect(await screen.findByText(/invalid registration data/i)).toBeInTheDocument();
  expect(await screen.findByText(/full name is required/i)).toBeInTheDocument();
});
