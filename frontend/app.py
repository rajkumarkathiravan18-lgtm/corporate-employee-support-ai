

import asyncio
import logging
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.workflow import SupportDesk
from backend.rag.retrieval import DATA, Knowledge


load_dotenv(ROOT / ".env")
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Employee Service Desk",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    color-scheme: light;
}

html, body, [class*="css"], [data-testid="stApp"] {
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            circle at 76% 7%,
            rgba(167,243,208,.26),
            transparent 29rem
        ),
        radial-gradient(
            circle at 16% 66%,
            rgba(191,219,254,.25),
            transparent 25rem
        ),
        #f6f8fb;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background: #10283b;
    border-right: 1px solid #244054;
}

/* Color sidebar copy without changing text inside white controls. */
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: #e8f2f4;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #b8d4dc;
}

/* Employee selector: dark text on white. */
[data-testid="stSidebar"] [data-baseweb="select"] {
    background: #ffffff;
    border-radius: 12px;
}

[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] [data-baseweb="select"] input {
    color: #173449 !important;
    opacity: 1 !important;
}

/* New conversation button: dark text on a light background. */
[data-testid="stSidebar"] .stButton button {
    border-radius: 12px;
    background: #e8fff3;
    border-color: #b9e9d3;
    color: #173449;
}

[data-testid="stSidebar"] .stButton button *,
[data-testid="stSidebar"] .stButton button p {
    color: #173449 !important;
    opacity: 1 !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background: #d2f7e5;
    border-color: #57cba2;
}

.block-container {
    max-width: 1160px;
    padding-top: 2rem;
    padding-bottom: 8rem;
}

h1, h2, h3 {
    font-family: 'Manrope', sans-serif;
    letter-spacing: -.035em;
}

.hero {
    padding: 2.2rem 2.5rem;
    border-radius: 26px;
    background: linear-gradient(
        113deg,
        #123448 0%,
        #173b49 60%,
        #176153 100%
    );
    color: #fff;
    box-shadow: 0 20px 48px rgba(13,54,71,.13);
    position: relative;
    overflow: hidden;
}

.hero:after {
    content: '';
    position: absolute;
    width: 230px;
    height: 230px;
    right: -45px;
    top: -85px;
    border-radius: 50%;
    border: 38px solid rgba(167,243,208,.11);
}

.hero .eyebrow {
    color: #9ef2ce;
    font-weight: 800;
    font-size: .75rem;
    letter-spacing: .18em;
    text-transform: uppercase;
    margin-bottom: .75rem;
}

.hero h1 {
    color: #fff;
    margin: 0;
    font-size: clamp(2rem, 4vw, 3.15rem);
    font-weight: 800;
}

.hero p {
    color: #d5e9ed;
    margin: .75rem 0 0;
    font-size: 1.03rem;
    max-width: 670px;
}

.section-label {
    color: #586b7c;
    font-size: .76rem;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 800;
    margin: 1.7rem 0 .65rem;
}

.sidebar-brand {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 1.22rem;
    margin: .35rem 0 0;
}

.sidebar-sub {
    color: #b8d4dc !important;
    font-size: .85rem;
    margin-bottom: 1.6rem;
}

.sidebar-mini {
    color: #a9c7d0 !important;
    font-size: .78rem;
    line-height: 1.5;
}

[data-testid="stChatMessage"] {
    background: #fff;
    border: 1px solid #e6edf3;
    border-radius: 18px;
    padding: .35rem .65rem;
    box-shadow: 0 8px 24px rgba(25,57,77,.04);
    margin-bottom: .75rem;
}

[data-testid="stChatMessage"]
[data-testid="stMarkdownContainer"] p {
    line-height: 1.65;
}

[data-testid="stChatInput"] {
    border-radius: 18px;
    box-shadow: 0 8px 28px rgba(27,54,72,.10);
}

.stButton button {
    border-radius: 13px;
    min-height: 2.65rem;
    border-color: #dce7ed;
    font-weight: 650;
}

.stButton button:hover {
    border-color: #159f85;
    color: #137b67;
}

[data-testid="stAlert"] {
    border-radius: 16px;
}

.status-note {
    font-size: .79rem;
    color: #6b7b89;
    margin-top: 1.5rem;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

EXAMPLES = [
    ("Leave balance", "How many casual leaves do I have?"),
    ("Travel policy", "How do I book travel for a client meeting?"),
    ("IT help", "My VPN is not connecting. What should I do?"),
    ("Expense claims", "How do I claim a work expense?"),
]


def error_message(exc: Exception) -> str:
    logger.exception("Employee support request failed")

    if getattr(exc, "status_code", None) == 400:
        body = getattr(exc, "body", None)
        param = None

        if isinstance(body, dict):
            error = body.get("error")
            param = (
                error.get("param")
                if isinstance(error, dict)
                else body.get("param")
            )

        return (
            "The AI provider rejected the request (HTTP 400). "
            f"Parameter: {param or 'unspecified'}. "
            "See the terminal for details."
        )

    return (
        f"Application error: {type(exc).__name__}. "
        "See the terminal for details."
    )


@st.cache_resource(show_spinner="Loading company policies...")
def get_knowledge(api_key: str, embedding_model: str):
    return Knowledge(api_key, embedding_model)


async def respond(
    question: str,
    employee: str,
    history: list,
    confirm: bool = False,
) -> dict:
    embedding_model = os.getenv(
        "EMBEDDING_MODEL",
        "text-embedding-3-small",
    )

    # Ticket confirmation does not need document retrieval.
    knowledge = (
        None
        if confirm
        else get_knowledge(
            os.environ["OPENAI_API_KEY"],
            embedding_model,
        )
    )

    desk = SupportDesk(
        os.environ["OPENAI_API_KEY"],
        os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model,
        knowledge=knowledge,
        skip_knowledge=confirm,
    )

    try:
        if confirm:
            return await desk.confirm_it_ticket(
                employee,
                question,
            )

        return await desk.ask(
            question,
            employee,
            history,
        )
    finally:
        await desk.close()


def run_request(
    question: str,
    employee: str,
    history: list,
    confirm: bool = False,
) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "answer": (
                "Add OPENAI_API_KEY to your .env file "
                "and restart the app."
            ),
            "route": [],
            "sources": [],
            "status": "error",
        }

    try:
        return asyncio.run(
            respond(question, employee, history, confirm)
        )
    except Exception as exc:
        return {
            "answer": error_message(exc),
            "route": [],
            "sources": [],
            "status": "error",
        }


if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_ticket" not in st.session_state:
    st.session_state.pending_ticket = None

if "active_employee" not in st.session_state:
    st.session_state.active_employee = "EMP001"


with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        "◈  Employee Service Desk"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-sub">'
        "Policies · Requests · Support"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Demo workspace")

    employee = st.selectbox(
        "Employee account",
        ["EMP001", "EMP002"],
    )

    if employee != st.session_state.active_employee:
        st.session_state.active_employee = employee
        st.session_state.messages = []
        st.session_state.pending_ticket = None
        st.rerun()

    st.caption(
        "This selector is a demo. It does not verify identity."
    )

    st.divider()
    st.markdown("### Support areas")

    st.markdown(
        "Leave & HR  \n"
        "Payroll & benefits  \n"
        "Finance & claims  \n"
        "IT & access  \n"
        "Travel & facilities"
    )

    st.divider()

    if st.button(
        "↻  New conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.pending_ticket = None
        st.rerun()

    st.markdown(
        '<p class="sidebar-mini">'
        "Assignment demo · Sample policies and simulated "
        "employee records. Do not enter real personal information."
        "</p>",
        unsafe_allow_html=True,
    )


st.markdown(
    '<div class="hero">'
    '<div class="eyebrow">'
    "Employee service desk · Demo"
    "</div>"
    "<h1>How can we help today?</h1>"
    "<p>Ask about policies, check a sample record, or raise "
    "an IT issue. Your request is routed to the relevant "
    "support area.</p>"
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-label">Start with a question</div>',
    unsafe_allow_html=True,
)

cols = st.columns(4, gap="small")
clicked_prompt = None

for col, (label, question) in zip(cols, EXAMPLES):
    with col:
        if st.button(
            label,
            use_container_width=True,
            key=f"example_{label}",
        ):
            clicked_prompt = question

st.markdown(
    '<div class="section-label">Conversation</div>',
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.info(
        "Choose a topic above or write your own question below.",
        icon="💬",
    )

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])

        if item["role"] == "assistant":
            route = item.get("route") or []
            sources = item.get("sources") or []

            if route:
                st.caption(
                    "Handled by: "
                    + " + ".join(
                        name.title()
                        for name in route
                    )
                )

            if item.get("status") in (
                "escalated",
                "blocked",
                "error",
            ):
                st.caption(
                    "Status: "
                    + item["status"]
                    .replace("_", " ")
                    .title()
                )

            if sources:
                with st.expander(
                    f"Policy references ({len(sources)})"
                ):
                    for source in sources:
                        path = DATA / source

                        if path.name != source or not path.is_file():
                            continue

                        st.markdown(f"**{source}**")
                        st.markdown(
                            path.read_text(encoding="utf-8")
                        )


if st.session_state.pending_ticket:
    pending = st.session_state.pending_ticket

    st.warning(
        "Review your request before creating a demo IT ticket.",
        icon="⚠️",
    )
    st.caption(pending["question"])

    yes_col, no_col, _ = st.columns([1.6, 1, 3])

    with yes_col:
        confirm = st.button(
            "Create demo ticket",
            type="primary",
            use_container_width=True,
        )

    with no_col:
        cancel = st.button(
            "Cancel",
            use_container_width=True,
        )

    if cancel:
        st.session_state.pending_ticket = None
        st.rerun()

    if confirm:
        with st.status(
            "Creating your demo ticket...",
            expanded=False,
        ):
            result = run_request(
                pending["question"],
                employee,
                pending["history"],
                confirm=True,
            )

        st.session_state.pending_ticket = None

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "route": result.get("route", []),
            "sources": result.get("sources", []),
            "status": result.get("status", "answered"),
        })

        st.rerun()


typed_prompt = st.chat_input(
    "Describe your question or support issue..."
)

prompt = typed_prompt or clicked_prompt

if prompt:
    if st.session_state.pending_ticket:
        st.session_state.pending_ticket = None

    previous = list(st.session_state.messages)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
    })

    with st.status(
        "Finding the right support team and reviewing the answer...",
        expanded=False,
    ):
        result = run_request(
            prompt,
            employee,
            previous,
        )

    if result.get("pending_action") == "create_it_ticket":
        st.session_state.pending_ticket = {
            "question": prompt,
            "history": previous,
        }

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "route": result.get("route", []),
        "sources": result.get("sources", []),
        "status": result.get("status", "answered"),
    })

    st.rerun()


st.markdown(
    '<p class="status-note">'
    "Demo only · AI answers depend on the supplied sample "
    "documents. Verify decisions with the responsible team."
    "</p>",
    unsafe_allow_html=True,
)