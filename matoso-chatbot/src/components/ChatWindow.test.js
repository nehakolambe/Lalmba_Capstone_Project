import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ChatWindow from './ChatWindow';
import {
  createThread,
  deleteThread,
  fetchHistory,
  fetchThreads,
  renameThread,
  resetChat,
  sendMessageStream
} from '../api';

jest.mock('../api', () => ({
  createThread: jest.fn(),
  deleteThread: jest.fn(),
  fetchHistory: jest.fn(),
  fetchThreads: jest.fn(),
  renameThread: jest.fn(),
  resetChat: jest.fn(),
  sendMessageStream: jest.fn()
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
  fetchHistory.mockResolvedValue({
    thread: defaultThread,
    history: [],
    session: {
      question_count: 0,
      question_limit: 10,
      questions_remaining: 10,
      limit_reached: false
    }
  });
  resetChat.mockResolvedValue({ thread: defaultThread });
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

test('sends a message and renders assistant response', async () => {
  sendMessageStream.mockImplementation(async (_threadId, _text, handlers = {}) => {
    handlers.onDelta?.('Mocked ');
    handlers.onDelta?.('assistant reply');
    return {
      type: 'done',
      thread: {
        ...defaultThread,
        title: 'Hello',
        updated_at: '2026-01-04T00:00:00'
      },
      message: { role: 'assistant', content: 'Mocked assistant reply' },
      session: {
        question_count: 1,
        question_limit: 10,
        questions_remaining: 9,
        limit_reached: false
      }
    };
  });

  const { container } = render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  expect(screen.getByText(/questions used 0\/10/i)).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/mocked assistant reply/i)).toBeInTheDocument();
  expect(screen.getByText(/questions used 1\/10/i)).toBeInTheDocument();
  expect(screen.getByText(/9 questions left in this chat/i)).toBeInTheDocument();
  await waitFor(() => expect(sendMessageStream).toHaveBeenCalledWith(101, 'Hello', expect.any(Object)));
});

test('renders assistant streaming chunks into one message bubble', async () => {
  let resolveStream;
  sendMessageStream.mockImplementation(async (_threadId, _text, handlers = {}) => {
    handlers.onDelta?.('Hello');
    handlers.onDelta?.(' there');
    return await new Promise(resolve => {
      resolveStream = () => resolve({
        type: 'done',
        thread: {
          ...defaultThread,
          updated_at: '2026-01-04T00:00:00'
        },
        message: { role: 'assistant', content: 'Hello there!' },
        session: {
          question_count: 1,
          question_limit: 10,
          questions_remaining: 9,
          limit_reached: false
        }
      });
    });
  });

  const { container } = render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/^hello there$/i)).toBeInTheDocument();
  expect(screen.getAllByText(/^hello there$/i)).toHaveLength(1);

  resolveStream();
  expect(await screen.findByText(/^hello there!$/i)).toBeInTheDocument();
});

test('does not render an empty assistant bubble before the first stream chunk arrives', async () => {
  let resolveStream;
  sendMessageStream.mockImplementation(async () => await new Promise(resolve => {
    resolveStream = () => resolve({
      type: 'done',
      thread: {
        ...defaultThread,
        updated_at: '2026-01-04T00:00:00'
      },
      message: { role: 'assistant', content: 'Final reply' },
      session: {
        question_count: 1,
        question_limit: 10,
        questions_remaining: 9,
        limit_reached: false
      }
    });
  }));

  const { container } = render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'what is a molecule' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(container.querySelectorAll('.chatgpt-messages .message-row.ai')).toHaveLength(2);
  expect(screen.getByText(/thinking/i)).toBeInTheDocument();

  resolveStream();
  expect(await screen.findByText(/final reply/i)).toBeInTheDocument();
});

test('repairs mojibake and renders simple markdown formatting in assistant replies', async () => {
  sendMessageStream.mockResolvedValue({
    type: 'done',
    thread: {
      ...defaultThread,
      updated_at: '2026-01-04T00:00:00'
    },
    message: {
      role: 'assistant',
      content: 'Ice forms at 0â¯Â°C.\n1. **Cool the water**\n2. **Freeze it**'
    },
    session: {
      question_count: 1,
      question_limit: 10,
      questions_remaining: 9,
      limit_reached: false
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'how is ice formed?' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/0\s*°C/i)).toBeInTheDocument();
  expect(screen.getByText(/cool the water/i).tagName).toBe('STRONG');
  expect(screen.getByText(/freeze it/i).tagName).toBe('STRONG');
});

test('handles auth error during send by surfacing message and logging out', async () => {
  const onLogout = jest.fn();
  sendMessageStream.mockRejectedValue({ status: 401, message: 'Unauthorized' });

  render(<ChatWindow user={user} onLogout={onLogout} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Help' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  const errors = await screen.findAllByText(/session has expired/i);
  expect(errors.length).toBeGreaterThan(0);
  await waitFor(() => expect(onLogout).toHaveBeenCalled());
});

test('falls back to non-streaming terminal payload when limit is reached', async () => {
  sendMessageStream.mockResolvedValue({
    thread: {
      ...defaultThread,
      updated_at: '2026-01-04T00:00:00'
    },
    messages: [{ role: 'assistant', content: 'You have reached the question limit for this chat.' }],
    session: {
      question_count: 10,
      question_limit: 10,
      questions_remaining: 0,
      limit_reached: true
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  fireEvent.change(screen.getByPlaceholderText(/send a message/i), {
    target: { value: 'Hello' }
  });
  fireEvent.click(screen.getByRole('button', { name: /^send$/i }));

  expect(await screen.findByText(/reached the question limit/i)).toBeInTheDocument();
  expect(screen.getByText(/questions used 10\/10/i)).toBeInTheDocument();
});

test('reset chat clears current history', async () => {
  fetchHistory.mockResolvedValue({
    thread: defaultThread,
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

  await waitFor(() => expect(resetChat).toHaveBeenCalledWith(101));
  expect(await screen.findByText(/hello alice!/i)).toBeInTheDocument();
  expect(screen.getByText(/questions used 0\/10/i)).toBeInTheDocument();
});

test('disables input when question limit is reached', async () => {
  fetchHistory.mockResolvedValue({
    thread: defaultThread,
    history: [],
    session: {
      question_count: 10,
      question_limit: 10,
      questions_remaining: 0,
      limit_reached: true
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  await screen.findByRole('button', { name: /^starter chat$/i });
  await screen.findByText(/0 questions left in this chat/i);
  expect(screen.getByPlaceholderText(/send a message/i)).toBeDisabled();
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

test('keeps multiline input visible and sends on enter', async () => {
  sendMessageStream.mockResolvedValue({
    type: 'done',
    thread: {
      ...defaultThread,
      updated_at: '2026-01-04T00:00:00'
    },
    message: { role: 'assistant', content: 'Thanks for the detailed question.' },
    session: {
      question_count: 1,
      question_limit: 10,
      questions_remaining: 9,
      limit_reached: false
    }
  });

  render(<ChatWindow user={user} onLogout={jest.fn()} />);

  const composer = await screen.findByPlaceholderText(/send a message/i);
  fireEvent.change(composer, { target: { value: 'First line' } });
  fireEvent.keyDown(composer, { key: 'Enter', code: 'Enter', shiftKey: true });
  fireEvent.change(composer, { target: { value: 'First line\nSecond line' } });

  expect(composer).toHaveValue('First line\nSecond line');

  fireEvent.keyDown(composer, { key: 'Enter', code: 'Enter' });

  await waitFor(() => expect(sendMessageStream).toHaveBeenCalledWith(101, 'First line\nSecond line', expect.any(Object)));
  expect(await screen.findByText(/thanks for the detailed question/i)).toBeInTheDocument();
});
