# Employee Service Desk — AutoGen assignment demo

Streamlit frontend and a modular Python backend. The manager routes each question to relevant AutoGen specialists; an evaluator checks the drafted answer. FAISS retrieves fictional policies; a local MCP server provides simulated employee records and ticket actions.

## Structure

```text
corporate_employee_ai/
├── frontend/app.py                 Streamlit interface and confirmation UI
├── backend/
│   ├── agents/__init__.py         AutoGen manager, specialists and evaluator
│   ├── orchestration/
│   │   ├── schemas.py             Structured routing and review outputs
│   │   └── workflow.py            Guarded request flow
│   ├── rag/retrieval.py           Domain-scoped FAISS retrieval + document cache
│   └── mcp/
│       ├── client.py              MCP stdio client
│       ├── server.py              MCP tools for demo data
│       └── storage.py             SQLite demo records and tickets
├── data/                          Fictional policies; generated demo database
├── tests/                         Offline workflow, retrieval and UI tests
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The backend is a Python package called by the Streamlit process. The MCP server runs as a local subprocess on a tool call. This project does not include a FastAPI or HTTP endpoint.

## Windows PowerShell setup

From a **fresh extraction** of this archive, open the `corporate_employee_ai` folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add your `OPENAI_API_KEY`. Start the UI:

```powershell
python -m streamlit run frontend/app.py
```

Try `travel`, `How many casual leaves do I have?`, `My VPN is not connecting`, `Create an IT ticket because my VPN fails after MFA`, and `What is the status of claim CLM100?` (EMP001). The ticket action asks for explicit confirmation. Tickets persist between MCP calls in the generated `data/demo_records.sqlite3` file. Delete that file to reset the fictional records.

## Verify

```powershell
python -m pytest -q tests
```

The tests exercise routing with simulated LLM decisions, retrieval cache and domain filtering, ticket confirmation, SQLite ownership, and Streamlit rendering. They do **not** validate responses from a live OpenAI model: that requires an API key, quota, and inspection of answers against your own policies. No real company policies or personnel records are included.

## Limits

The employee dropdown is a demo selector, not authentication. Data is fictional and intentionally incomplete: unsupported policy questions receive an escalation response. A production system needs SSO, server-derived identity, per-tool authorization, source document access rules, audit logging, a real ticketing system, and review of answer quality with company-specific evaluations. Do not put real employee data into this demo or expose it publicly.
