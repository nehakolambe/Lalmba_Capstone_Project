import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ChatWindow from './ChatWindow';
import { fetchHistory, resetChat, sendMessage } from '../api';

jest.mock('../api', () => ({
  fetchHistory: jest.fn(),
  resetChat: jest.fn(),
  sendMessage: jest.fn()
}));

const user = { id: 1, username: 'alice' };

beforeEach(() => {
  jest.clearAllMocks();
  fetchHistory.mockResolvedValue({
    history: [],
    session: {
      question_count: 0,
      question_limit: 10,
      questions_remaining: 10,
      limit_reached: false
    }
  });
  resetChat.mockResolvedValue({});
});

test('sends a message and renders assistant response', async () => {
  sendMessage.mockResolvedValue({
    messages: [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Mocked assistant reply' }
    ],
    session: {
      question_count: 1,
      question_limit: 10,
      questions_remaining: 9,
      limit_reached: false
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByText(/hello alice!/i);
  expect(screen.getByText(/questions used 0\/10/i)).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/mocked assistant reply/i)).toBeInTheDocument();
  expect(screen.getByText(/questions used 1\/10/i)).toBeInTheDocument();
  expect(screen.getByText(/9 questions left in this chat/i)).toBeInTheDocument();
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
  fetchHistory.mockResolvedValue({
    history: [
      { role: 'assistant', content: 'Previous response', created_at: '2026-01-01T00:00:00' }
    ],
    session: {
      question_count: 4,
      question_limit: 10,
      questions_remaining: 6,
      limit_reached: false
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);
  expect(await screen.findByText(/previous response/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /reset session/i }));

  await waitFor(() => expect(resetChat).toHaveBeenCalled());
  expect(await screen.findByText(/hello alice!/i)).toBeInTheDocument();
  expect(screen.getByText(/questions used 0\/10/i)).toBeInTheDocument();
});

test('disables input when question limit is reached', async () => {
  fetchHistory.mockResolvedValue({
    history: [],
    session: {
      question_count: 10,
      question_limit: 10,
      questions_remaining: 0,
      limit_reached: true
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByText(/hello alice!/i);
  await screen.findByText(/0 questions left in this chat/i);
  expect(screen.getByPlaceholderText(/send a message/i)).toBeDisabled();
});
