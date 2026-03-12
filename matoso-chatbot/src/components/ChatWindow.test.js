import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ChatWindow from './ChatWindow';
import {
  createThread,
  deleteThread,
  fetchHistory,
  fetchProgress,
  fetchThreads,
  recordProgress,
  renameThread,
  resetChat,
  sendMessage
} from '../api';

jest.mock('../api', () => ({
  createThread: jest.fn(),
  deleteThread: jest.fn(),
  fetchHistory: jest.fn(),
  fetchProgress: jest.fn(),
  fetchThreads: jest.fn(),
  recordProgress: jest.fn(),
  renameThread: jest.fn(),
  resetChat: jest.fn(),
  sendMessage: jest.fn()
}));

const user = { id: 1, username: 'alice' };
const defaultThread = {
  id: 101,
  title: 'Starter chat',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00'
};

beforeEach(() => {
  jest.clearAllMocks();
  fetchThreads.mockResolvedValue([defaultThread]);
  fetchHistory.mockResolvedValue([]);
  fetchProgress.mockResolvedValue([]);
  recordProgress.mockResolvedValue({ id: 1, milestone: 'Reflection 1' });
  resetChat.mockResolvedValue(defaultThread);
  createThread.mockResolvedValue({
    id: 202,
    title: 'New chat',
    created_at: '2026-01-02T00:00:00',
    updated_at: '2026-01-02T00:00:00'
  });
  renameThread.mockImplementation(async (threadId, title) => ({
    ...defaultThread,
    id: threadId,
    title,
    updated_at: '2026-01-03T00:00:00'
  }));
  deleteThread.mockResolvedValue({});
});

test('sends a message within the active thread and renders assistant response', async () => {
  sendMessage.mockResolvedValue({
    thread: {
      ...defaultThread,
      title: 'Hello there',
      updated_at: '2026-01-04T00:00:00'
    },
    messages: [
      { id: 1, role: 'user', content: 'Hello' },
      { id: 2, role: 'assistant', content: 'Mocked assistant reply' }
    ]
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /send/i }));

  expect(await screen.findByText(/mocked assistant reply/i)).toBeInTheDocument();
  await waitFor(() => expect(sendMessage).toHaveBeenCalledWith(101, 'Hello'));
});

test('handles auth error during send by surfacing message and logging out', async () => {
  const onLogout = jest.fn();
  sendMessage.mockRejectedValue({ status: 401, message: 'Unauthorized' });

  render(<ChatWindow user={user} onLogout={onLogout} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Help' }
  });
  fireEvent.click(screen.getByRole('button', { name: /send/i }));

  const errors = await screen.findAllByText(/session has expired/i);
  expect(errors.length).toBeGreaterThan(0);
  await waitFor(() => expect(onLogout).toHaveBeenCalled());
});

test('reset session clears chat and progress state for the active thread', async () => {
  fetchProgress.mockResolvedValue([
    { id: 1, milestone: 'Reflection 1', notes: 'Saved note', created_at: '2026-01-01T00:00:00' }
  ]);

  render(<ChatWindow user={user} onLogout={jest.fn()} />);
  await screen.findByRole('button', { name: /^starter chat$/i });
  expect(await screen.findByText(/session progress 1\/10/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /reset session/i }));

  await waitFor(() => expect(resetChat).toHaveBeenCalledWith(101));
  expect(await screen.findByText(/session progress 0\/10/i)).toBeInTheDocument();
  expect(await screen.findByText(/hello alice!/i)).toBeInTheDocument();
});

test('creates and renames chats from the sidebar', async () => {
  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  expect(await screen.findByRole('button', { name: /^starter chat$/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /create new chat/i }));
  expect(await screen.findByRole('button', { name: /^new chat$/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /more actions for new chat/i }));
  fireEvent.click(screen.getByRole('button', { name: /^rename$/i }));
  fireEvent.change(screen.getByDisplayValue(/new chat/i), {
    target: { value: 'Project ideas' }
  });
  fireEvent.click(screen.getByRole('button', { name: /save/i }));

  await waitFor(() => expect(renameThread).toHaveBeenCalledWith(202, 'Project ideas'));
  expect(await screen.findByRole('button', { name: /^project ideas$/i })).toBeInTheDocument();
});
