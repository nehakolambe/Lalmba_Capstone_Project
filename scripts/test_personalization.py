import os
import sys
from textwrap import shorten

import requests


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def ensure_user(username, pin, full_name):
    session = requests.Session()
    register_payload = {
        "username": username,
        "pin": pin,
        "fullName": full_name,
        "details": "automation test user",
    }
    reg = session.post(f"{BASE_URL}/auth/register", json=register_payload, timeout=10)
    if reg.status_code == 201:
        return session
    if reg.status_code != 409:
        raise RuntimeError(f"Register failed for {username}: {reg.status_code} {reg.text}")

    login_payload = {"username": username, "pin": pin}
    login = session.post(f"{BASE_URL}/auth/login", json=login_payload, timeout=10)
    if login.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {login.status_code} {login.text}")
    return session


def set_questionnaire(session, answers):
    res = session.post(
        f"{BASE_URL}/questionnaire/me",
        json={"answers": answers},
        timeout=10,
    )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Questionnaire save failed: {res.status_code} {res.text}")


def send_chat(session, text):
    res = session.post(f"{BASE_URL}/chat/message", json={"text": text}, timeout=60)
    if res.status_code != 201:
        raise RuntimeError(f"Chat failed: {res.status_code} {res.text}")
    data = res.json()
    messages = data.get("messages") or []
    assistant = next((m for m in reversed(messages) if m.get("role") == "assistant"), None)
    reply = assistant.get("content") if assistant else ""
    debug_profile = data.get("debug_profile")
    return reply, debug_profile


def contains_any(text, keywords):
    return any(k in text for k in keywords)


def main():
    prompt = "Teach me how to use a computer."

    user_a_answers = {
        "name": "User A",
        "language_preference": "English",
        "literacy_level": "Beginner",
        "typing_comfort": "Low",
        "learning_goals": ["Improve computer basics"],
        "topics_interest": ["Documents & typing"],
        "hours_per_week": "1",
        "prior_experience": "Very little",
        "help_today": "Learn basics",
        "consent": True,
    }

    user_b_answers = {
        "name": "User B",
        "language_preference": "English",
        "literacy_level": "Advanced",
        "typing_comfort": "High",
        "learning_goals": ["Spreadsheets", "Job readiness"],
        "topics_interest": ["Spreadsheets", "Internet & email"],
        "hours_per_week": "10",
        "prior_experience": "Comfortable with computers",
        "help_today": "Improve office skills",
        "consent": True,
    }

    session_a = ensure_user("persona_a", "1234", "Persona A")
    session_b = ensure_user("persona_b", "1234", "Persona B")

    set_questionnaire(session_a, user_a_answers)
    set_questionnaire(session_b, user_b_answers)

    reply_a, profile_a = send_chat(session_a, prompt)
    reply_b, profile_b = send_chat(session_b, prompt)

    print("== Personalization Comparison ==")
    print(f"Base URL: {BASE_URL}")
    print("\nUser A profile:")
    print(profile_a or "(debug_profile not returned; set FLASK_ENV=development)")
    print("User A reply (first 300 chars):")
    print(shorten(reply_a, width=300, placeholder="..."))

    print("\nUser B profile:")
    print(profile_b or "(debug_profile not returned; set FLASK_ENV=development)")
    print("User B reply (first 300 chars):")
    print(shorten(reply_b, width=300, placeholder="..."))

    if profile_a and profile_b:
        assert profile_a != profile_b, "Expected different debug profiles for User A vs User B"
    else:
        print("\nWARN: debug_profile missing. Enable FLASK_ENV=development to assert profiles.")

    reply_a_lower = reply_a.lower()
    reply_b_lower = reply_b.lower()

    assert reply_a != reply_b, "Replies should not be identical."
    assert contains_any(
        reply_a_lower,
        ["step", "click", "yes", "no", "first", "next"],
    ), "User A reply missing beginner-friendly cues."
    assert contains_any(
        reply_b_lower,
        ["spreadsheet", "job", "practice", "exercise", "task"],
    ), "User B reply missing advanced goal cues."

    print("\nOK: Personalization checks passed.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\nFAIL: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)
