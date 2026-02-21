import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ChatWindow from './ChatWindow';
import {
  fetchHistory,
  fetchProgress,
  recordProgress,
  resetChat,
  sendMessage
} from '../api';

jest.mock('../api', () => ({
  fetchHistory: jest.fn(),
  fetchProgress: jest.fn(),
  recordProgress: jest.fn(),
  resetChat: jest.fn(),
  sendMessage: jest.fn()
}));

const user = { id: 1, username: 'alice' };

beforeEach(() => {
  jest.clearAllMocks();
  fetchHistory.mockResolvedValue([]);
  fetchProgress.mockResolvedValue([]);
  recordProgress.mockResolvedValue({ id: 1, milestone: 'Reflection 1' });
  resetChat.mockResolvedValue({});
});

test('sends a message and renders assistant response', async () => {
  sendMessage.mockResolvedValue([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Mocked assistant reply' }
  ]);

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByText(/hello alice!/i);
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/mocked assistant reply/i)).toBeInTheDocument();
  await waitFor(() => expect(sendMessage).toHaveBeenCalledWith('Hello'));
});

test('handles auth error during send by surfacing message and logging out', async () => {
  const onLogout = jest.fn();
  sendMessage.mockRejectedValue({ status: 401, message: 'Unauthorized' });

  render(<ChatWindow user={user} onLogout={onLogout} />);

  await screen.findByText(/hello alice!/i);
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Help' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  const errors = await screen.findAllByText(/session has expired/i);
  expect(errors.length).toBeGreaterThan(0);
  await waitFor(() => expect(onLogout).toHaveBeenCalled());
});

test('reset chat clears current history', async () => {
  fetchHistory.mockResolvedValue([
    { role: 'assistant', content: 'Previous response', created_at: '2026-01-01T00:00:00' }
  ]);

  render(<ChatWindow user={user} onLogout={jest.fn()} />);
  expect(await screen.findByText(/previous response/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /reset chat/i }));

  await waitFor(() => expect(resetChat).toHaveBeenCalled());
  expect(await screen.findByText(/hello alice!/i)).toBeInTheDocument();
});
