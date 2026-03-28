from __future__ import annotations

from backend.services.chat_threads import build_auto_thread_title


def test_build_auto_thread_title_uses_first_question_as_is():
    assert build_auto_thread_title("What is fire?") == "What is fire?"


def test_build_auto_thread_title_normalizes_extra_whitespace():
    assert build_auto_thread_title("  Explain   photosynthesis   in plants  ") == "Explain photosynthesis in plants"


def test_build_auto_thread_title_truncates_long_questions():
    long_question = "Please explain the difference between plant and animal cells in simple detail for me"
    assert build_auto_thread_title(long_question) == "Please explain the difference between plant and animal c..."
