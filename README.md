# Children's Oral Health Support

A mobile-friendly experimental chatbot that helps parents and carers find clear, safety-focused information about children's oral health.

> **Important:** This is a university research prototype. It does not diagnose conditions, replace a dentist or other healthcare professional, or represent an official NHS service. If a child has difficulty breathing, uncontrolled bleeding, severe swelling, or another medical emergency, seek urgent professional help immediately.

## What the prototype does

The application provides:

- general prevention and toothbrushing guidance;
- age-aware information for children aged 0–3, 3–6, and 7+;
- guidance for toothache and dental injuries;
- deterministic safety checks before any AI-generated response;
- reviewed local knowledge retrieval with visible source links;
- optional Hugging Face model responses with automatic fallback;
- England NHS dentist-directory searches when an NHS API key is configured;
- experimental offline Wales dental-directory results; and
- a mobile-friendly chat interface with location and age controls.

The Wales results are an offline directory snapshot. They do not show live appointment availability or confirm whether a practice is accepting NHS patients. Users should always contact a practice directly.

## Technology

- **Frontend:** React, TypeScript, and Vite
- **Backend:** Python, FastAPI, and Uvicorn
- **Tests:** pytest and FastAPI TestClient
- **Optional services:** Hugging Face Inference and the NHS Service Search integration API

## Project structure

```text
oral-health-chatbot/
├── backend/
│   ├── main.py
│   ├── safety.py
│   ├── knowledge.py
│   ├── llm.py
│   ├── nhs_services.py
│   ├── rate_limit.py
│   ├── schemas.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── tests/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docs/
└── README.md
```

## Downloading the experimental version

The latest experimental code is on the **`Experimental`** branch.

### Download without Git

1. Open the repository on GitHub.
2. Select the **`Experimental`** branch from the branch menu.
3. Select **Code**, then **Download ZIP**.
4. Extract the ZIP file before following the setup steps below.

### Clone with Git

```bash
git clone --branch Experimental https://github.com/ccyyyyyyymust-lgtm/oral-health-chatbot.git
cd oral-health-chatbot
```

## Local setup

### Prerequisites

Install Python 3, Node.js and npm. Git is only required when cloning the repository.

A Python virtual environment is strongly recommended because it keeps the project's packages separate from other Python projects. Either `venv` or Conda can be used.

### 1. Create and activate a Python environment

Using `venv` on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Using `venv` on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Alternatively, using Conda:

```bash
conda create -n oral-health-chatbot python -y
conda activate oral-health-chatbot
```

### 2. Install and start the backend

From the repository root:

```bash
cd backend
python -m pip install -r requirements-dev.txt
```

Copy `backend/.env.example` to `backend/.env`. The application works without external API credentials by using its tested local fallback. Optional integrations can be enabled in `backend/.env`:

```env
HF_TOKEN=
HF_MODEL=
HF_PROVIDER=auto
LLM_TIMEOUT_SECONDS=12
LLM_TEMPERATURE=0.2

NHS_API_KEY=
NHS_SERVICE_SEARCH_BASE_URL=https://int.api.service.nhs.uk/service-search-api/
NHS_API_TIMEOUT_SECONDS=10

RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW_SECONDS=60
```

Never commit API keys or the real `.env` file to GitHub.

Start the backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

The backend will be available at `http://127.0.0.1:8000`, and the interactive API documentation will be at `http://127.0.0.1:8000/docs`.

### 3. Install and start the frontend

Open a second terminal, return to the repository root, and run:

```bash
cd frontend
npm install
npm run dev
```

Open the address displayed by Vite, normally `http://localhost:5173`.

For a separately deployed backend, copy `frontend/.env.example` to `frontend/.env` and set:

```env
VITE_API_URL=https://your-backend.example.com
```

## Run the tests

With the Python environment activated:

```bash
cd backend
python -m pytest -q
```

To check the production frontend build:

```bash
cd frontend
npm run build
```

## How responses are produced

1. The backend checks the message for urgent safety indicators.
2. It identifies relevant reviewed guidance and regional information.
3. If Hugging Face is configured, the model receives the recent conversation and retrieved evidence.
4. If the external model is unavailable, the application returns a deterministic or retrieval-based fallback.
5. Supporting source links are returned to the frontend for display.

Safety routing runs before model generation. External model output is therefore not used as the only protection for emergency wording.

## Current limitations

- The project is an experimental demonstration, not a production medical device.
- Information may be incomplete and must not be treated as a diagnosis.
- England directory searches depend on access to the NHS integration environment.
- Wales directory results are offline listings rather than live search results.
- Availability, NHS acceptance, opening hours, and contact details should be confirmed directly with the dental practice.
- The configured APIs, data sources, and model may change during development.

## Data and privacy

Do not enter real patient-identifiable or confidential information when testing the prototype. API tokens must remain in local environment files and must never be placed in frontend code or committed to the repository.

## Branches

- **`main`** — earlier stable project history
- **`Experimental`** — latest experimental implementation for review and local testing

## Feedback

If you encounter a setup problem or identify unsafe, unclear, or unsupported guidance, please open a GitHub issue with the steps needed to reproduce it. Do not include personal health information or API credentials in an issue.
