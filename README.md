# ProcureAI — AI-Powered Procurement Assistant

ProcureAI is an AI-powered procurement assistant that helps users explore and analyze public procurement data through natural-language questions.

The application uses a React frontend, a Python/FastAPI backend, and MongoDB for data storage. LangGraph coordinates question processing. Common questions can use optimized, deterministic queries to reduce unnecessary AI-model calls, while Google Gemini helps generate MongoDB aggregation queries for more complex requests. Generated queries are validated before execution, and the application uses a read-only MongoDB account for safer access.

MongoDB runs locally in a Docker container managed by Docker Compose. The frontend and backend are run separately during local development.

## Features

- Ask procurement questions in natural language, including informal phrasing.
- View an at-a-glance dashboard of procurement statistics.
- Use optimized queries for supported common questions.
- Generate MongoDB aggregation queries with Google Gemini for more complex questions.
- Validate generated aggregation queries before execution.
- Analyze spending, departments, suppliers, line items, and purchases.
- Display results through a React web interface.
- Use a read-only MongoDB account for additional database protection.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| AI Model | Google Gemini |
| AI Framework | LangChain, LangGraph |
| Database | MongoDB |
| Database Driver | PyMongo |
| Local database infrastructure | Docker Compose |

## Requirements

Before running the project, install or obtain:

- Python 3.12
- Node.js and npm
- Docker Desktop with Docker Compose
- A Google Gemini API key
- The procurement CSV dataset (download instructions below)

The commands below use PowerShell on Windows.

## Project Structure

```text
ai-procurement-assistant/
|
+-- backend/
|   +-- agent.py
|   +-- answer_generator.py
|   +-- database.py
|   +-- fast_queries.py
|   +-- import_data.py
|   +-- main.py
|   +-- procurement_agent.py
|   +-- query_executor.py
|   +-- query_generator.py
|   +-- query_validator.py
|   +-- quick_test.py
|   +-- setup_mongodb_user.py
|   +-- test_assessment_regressions.py
|   +-- test_clock_regressions.py
|   +-- test_gemini.py
|   +-- test_mongodb.py
|   +-- test_readonly.py
|   +-- test_regressions.py
|   +-- test_speed_regressions.py
|
+-- fronted/                 # Directory name is intentionally "fronted"
|   +-- src/
|   +-- package.json
|   +-- vite.config.js
|
+-- data/                    # Place downloaded CSV here (not committed to Git)
|   +-- purchases_cleaned.csv
|
+-- docker-compose.yml
+-- requirements.txt
+-- .env                     # Create locally; do not commit
+-- README.md
```

> **Note:** The frontend directory is named `fronted` in this project. The CSV and `.env` are local files and should not be committed to the repository.

## Installation and Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/Hassan-cp/ProcureAI.git
cd ProcureAI
```

### 2. Create the Python Virtual Environment

From the project root:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key
MONGO_ROOT_PASSWORD=your_mongodb_root_password
MONGO_READER_USERNAME=procurement_reader
MONGO_READER_PASSWORD=your_mongodb_reader_password
```

Replace the placeholders with your own credentials. **Never commit `.env`, API keys, or database passwords.**

### 5. Start MongoDB with Docker Compose

Start Docker Desktop. From the project root, run:

```powershell
docker compose up -d
```

The project's Docker Compose configuration runs MongoDB locally on port `27017`.

### 6. Create the Read-Only MongoDB User

```powershell
python backend/setup_mongodb_user.py
```

The setup script creates a MongoDB user with the `read` role on the `procurement_db` database. If the user already exists with the expected role, the script leaves it unchanged.

### 7. Download and Import the Procurement Data

Download the dataset from the link in the [Dataset](#dataset) section, and save it at:

```text
data/purchases_cleaned.csv
```

Then run:

```powershell
python backend/import_data.py
```

The import script loads procurement records into the MongoDB `purchases` collection. It skips importing when records already exist.

### 8. Start the Backend

From the project root, with the Python environment activated:

```powershell
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

- Backend: `http://127.0.0.1:8001`
- API documentation: `http://127.0.0.1:8001/docs`

### 9. Start the Frontend

Open a second terminal in the project root:

```powershell
cd fronted
npm install
npm run dev
```

Open the local address displayed by Vite, normally `http://localhost:5173`.

## How Questions Are Processed

1. The user enters a question in the React interface.
2. The frontend sends the question to the FastAPI backend.
3. LangGraph coordinates the question-processing workflow.
4. Supported common questions use optimized query logic; more complex questions may use Google Gemini to generate an aggregation pipeline.
5. Generated queries are validated before execution.
6. The backend executes allowed read-only MongoDB queries and formats the results for the frontend.

This separation keeps the interface, orchestration, query validation, and database execution organized.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Backend health check |
| GET | `/api/stats` | Procurement statistics |
| GET | `/api/total-spending` | Total procurement spending |
| POST | `/api/ask` | Ask a procurement question |

## Example Questions

- How many purchases are in the database?
- What is the total procurement spending?
- Which year-quarter had the highest total spending?
- Which departments have the highest spending?
- Who are the top suppliers by spending?
- What are the most frequently ordered line items?
- What are the latest purchases?

## Security Measures

ProcureAI includes several safeguards:

1. A dedicated MongoDB user with read-only permissions.
2. Validation of AI-generated MongoDB aggregation pipelines.
3. Rejection of prohibited aggregation operations.
4. Environment variables for sensitive credentials.
5. MongoDB access restricted to localhost through Docker Compose.

These controls reduce risk but do not guarantee protection against every possible attack. Additional review would be needed before production deployment.

## Testing

The project includes test scripts for query correctness, security, date handling, performance, and integration checks.

| File | Purpose |
|---|---|
| `backend/test_assessment_regressions.py` | Quarter semantics, qualifiers, query validation, fast-path behavior, date filtering, and result ordering |
| `backend/test_clock_regressions.py` | Date- and time-related regression checks |
| `backend/test_speed_regressions.py` | Performance-related regression checks |
| `backend/test_regressions.py` | Regression checks for previously identified issues |
| `backend/test_readonly.py` | Read-only database access checks |
| `backend/test_mongodb.py` | MongoDB connectivity checks |
| `backend/test_gemini.py` | Gemini integration checks |
| `backend/quick_test.py` | Automated procurement question checks |

### Run the Assessment Regression Suite

From the project root, with the Python environment activated:

```powershell
cd backend
python -m unittest test_assessment_regressions -v
```

This suite contains **six test methods**. A successful run ends with `OK`.

### Run the Automated Question Checks

From the project root, with the backend running:

```powershell
python backend/quick_test.py
```

ChatGPT Work was used to help create tests, review code, and identify issues. The application was also tested manually through the web interface. Passing automated checks does not guarantee every AI-generated answer will be accurate.

## Dataset

The development database contains **346,018 procurement records**. The data includes purchases, departments, suppliers, prices, and dates.

The CSV dataset is **not included in Git** because of its size. Download it separately and save it as `data/purchases_cleaned.csv` before running the import script.

**Dataset download:** [purchases_cleaned.csv (Google Drive)](https://drive.google.com/file/d/1aD2y-5ooneDEWf6UY2WKeQ1lCPPZmRiH/view?usp=sharing)

## Limitations

- AI-generated answers may occasionally be inaccurate.
- Complex query generation depends on the availability of the Gemini API.
- MongoDB and the procurement dataset must be configured before use.
- The application is designed for local development and demonstration.
- Additional testing, deployment configuration, and security review would be required for production use.

## Project Purpose

ProcureAI demonstrates the integration of natural-language processing, large language models, database query generation and validation, backend APIs, and a frontend interface. Its goal is to make procurement data easier to explore without requiring users to write MongoDB queries manually.
