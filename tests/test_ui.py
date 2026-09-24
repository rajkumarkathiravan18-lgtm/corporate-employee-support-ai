from pathlib import Path

import dotenv
from streamlit.testing.v1 import AppTest


def prevent_api_calls(monkeypatch):
    # The app normally loads .env at import time.
    # UI tests must never read a real API key.
    monkeypatch.setattr(
        dotenv,
        "load_dotenv",
        lambda *args, **kwargs: False,
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_dashboard_and_topic_button_render_without_key(monkeypatch):
    prevent_api_calls(monkeypatch)

    path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "app.py"
    )
    app = AppTest.from_file(str(path), default_timeout=15).run()

    assert not app.exception
    assert len(app.button) >= 4

    app.button(key="example_Travel policy").click().run()

    assert not app.exception
    assert len(app.chat_message) == 2
    assert (
        "Add OPENAI_API_KEY"
        in app.chat_message[1].markdown[0].value
    )


def test_ticket_confirmation_screen_renders(monkeypatch):
    prevent_api_calls(monkeypatch)

    path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "app.py"
    )
    app = AppTest.from_file(str(path), default_timeout=15)

    app.session_state["pending_ticket"] = {
        "question": "Create a ticket: VPN fails after MFA",
        "history": [],
    }

    app.run()

    assert not app.exception
    assert any(
        button.label == "Create demo ticket"
        for button in app.button
    )