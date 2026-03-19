import React, { useEffect, useRef, useState } from 'react';

function ChatSidebar({
  darkMode,
  threads,
  activeThreadId,
  creatingThread,
  renamingThreadId,
  renameValue,
  threadBusyId,
  onCreateThread,
  onSelectThread,
  onStartRename,
  onRenameValueChange,
  onRenameSubmit,
  onRenameCancel,
  onDeleteThread
}) {
  const MENU_WIDTH = 132;
  const MENU_OVERLAP = 54;
  const [menuState, setMenuState] = useState(null);
  const sidebarRef = useRef(null);

  const openMenuThread = threads.find(thread => thread.id === menuState?.id) || null;

  useEffect(() => {
    function handleClickOutside(event) {
      if (!sidebarRef.current?.contains(event.target)) {
        setMenuState(null);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    function handleScrollOrResize() {
      setMenuState(null);
    }

    window.addEventListener('resize', handleScrollOrResize);
    document.addEventListener('scroll', handleScrollOrResize, true);

    return () => {
      window.removeEventListener('resize', handleScrollOrResize);
      document.removeEventListener('scroll', handleScrollOrResize, true);
    };
  }, []);

  function handleMenuToggle(threadId, event) {
    if (menuState?.id === threadId) {
      setMenuState(null);
      return;
    }

    const triggerRect = event.currentTarget.getBoundingClientRect();
    setMenuState({
      id: threadId,
      top: triggerRect.bottom + 6,
      left: triggerRect.right - MENU_OVERLAP
    });
  }

  return (
    <aside ref={sidebarRef} className={`chat-sidebar ${darkMode ? 'dark' : 'light'}`}>
      <button
        type="button"
        className={`new-chat-btn ${darkMode ? 'dark' : 'light'}`}
        onClick={onCreateThread}
        disabled={creatingThread}
        aria-label="Create new chat"
      >
        {creatingThread ? 'Creating...' : '+ New chat'}
      </button>

      <div className="chat-thread-list">
        {threads.map(thread => {
          const isActive = thread.id === activeThreadId;
          const isRenaming = thread.id === renamingThreadId;
          const isBusy = thread.id === threadBusyId;

          return (
            <div
              key={thread.id}
              className={`chat-thread-item ${isActive ? 'active' : ''} ${darkMode ? 'dark' : 'light'}`}
            >
              {isRenaming ? (
                <form
                  className="chat-thread-rename"
                  onSubmit={event => {
                    event.preventDefault();
                    onRenameSubmit(thread.id);
                  }}
                >
                  <input
                    value={renameValue}
                    onChange={event => onRenameValueChange(event.target.value)}
                    maxLength={255}
                    autoFocus
                  />
                  <div className="chat-thread-rename-actions">
                    <button type="submit" disabled={isBusy}>Save</button>
                    <button type="button" onClick={onRenameCancel} disabled={isBusy}>Cancel</button>
                  </div>
                </form>
              ) : (
                <>
                  <button
                    type="button"
                    className="chat-thread-button"
                    onClick={() => onSelectThread(thread.id)}
                    disabled={isBusy}
                  >
                    <span className="chat-thread-title">{thread.title}</span>
                  </button>
                  <div className="chat-thread-menu">
                    <button
                      type="button"
                      className={`chat-thread-menu-trigger ${darkMode ? 'dark' : 'light'}`}
                      onClick={event => handleMenuToggle(thread.id, event)}
                      disabled={isBusy}
                      aria-label={`More actions for ${thread.title}`}
                    >
                      •••
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      {openMenuThread && (
        <div
          className={`chat-thread-menu-popover ${darkMode ? 'dark' : 'light'}`}
          style={{ position: 'fixed', top: menuState.top, left: menuState.left, width: MENU_WIDTH }}
        >
          <button
            type="button"
            className="chat-thread-menu-item"
            onClick={() => {
              setMenuState(null);
              onStartRename(openMenuThread);
            }}
            disabled={openMenuThread.id === threadBusyId}
          >
            Rename
          </button>
          <button
            type="button"
            className="chat-thread-menu-item delete"
            onClick={() => {
              setMenuState(null);
              onDeleteThread(openMenuThread);
            }}
            disabled={openMenuThread.id === threadBusyId}
          >
            Delete
          </button>
        </div>
      )}
    </aside>
  );
}

export default ChatSidebar;
