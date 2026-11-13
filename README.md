# ProcureAI — AI-Powered Procurement Assistant

ProcureAI is an AI-powered procurement assistant that allows users to explore and analyze public procurement data through natural-language questions.

The system uses Google Gemini to generate MongoDB aggregation queries, validates them before execution, and presents results through a React web interface.

## Features

- Ask procurement questions using natural language.
- Generate database queries with Google Gemini.
- Validate MongoDB aggregation queries before execution.
- Analyze procurement spending, departments, suppliers, and purchases.
- Display results through a modern React interface.
- Use a read-only MongoDB account for safer database access.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| AI Model | Google Gemini |
| AI Framework | LangChain, LangGraph |
| Database | MongoDB |
| Database Driver | PyMongo |
| Infrastructure | Docker Compose |

## Requirements

Before running the project, install:

- Python 3.12
- Node.js and npm
- Docker Desktop
- A Google Gemini API key
- The procurement CSV dataset

## Project Structure

```text
ai-procurement-assistant/
│
├── backend/
│   ├── agent.py
│   ├── answer_generator.py
│   ├── database.py
│   ├── import_data.py
│   ├── main.py
│   ├── procurement_agent.py
│   ├── query_executor.py
│   ├── query_generator.py
│   ├── query_validator.py
│   ├── quick_test.py
│   └── setup_mongodb_user.py
│
├── fronted/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   └── purchases_cleaned.csv
│
├── docker-compose.yml
├── requirements.txt
├── .env
└── README.md
```

**Note:** The frontend directory is named `fronted` in the current project.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-procurement-assistant
```

Replace `<repository-url>` with the actual Git repository URL.

### 2. Create the Python Virtual Environment

From the project root, run:

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

Replace the example values with your own credentials.

**Security:** Never commit `.env` or expose your API keys and passwords.

### 5. Start MongoDB

Make sure Docker Desktop is running.

From the project root:

```powershell
docker compose up -d
```

The MongoDB container will be accessible locally on port `27017`.

### 6. Create the Read-Only MongoDB User

Run:

```powershell
python backend/setup_mongodb_user.py
```

This script creates a MongoDB user with the `read` role on the `procurement_db` database.

If the user already exists with the expected role, the script leaves it unchanged.

### 7. Import Procurement Data

Place the cleaned procurement dataset at:

```text
data/purchases_cleaned.csv
```

Then run:

```powershell
python backend/import_data.py
```

The import script loads the procurement records into the MongoDB `purchases` collection.

**Note:** The dataset is not included in Git and must be supplied separately. The import script skips importing when records already exist.

### 8. Start the Backend

From the project root:

```powershell
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Backend URL:

`http://127.0.0.1:8001`

API documentation:

`http://127.0.0.1:8001/docs`

### 9. Start the Frontend

Open another terminal:

```powershell
cd fronted
npm install
npm run dev
```

Open the local address displayed by Vite, normally:

`http://localhost:5173`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Backend health check |
| GET | `/api/stats` | Procurement statistics |
| GET | `/api/total-spending` | Total procurement spending |
| POST | `/api/ask` | Ask a procurement question |

## Example Questions

Users can ask questions such as:

- How many purchases are in the database?
- What is the total procurement spending?
- Which departments have the highest spending?
- What are the most expensive purchases?
- How many purchases were made by the Department of Transportation?
- What are the latest purchases?

## Security Measures

ProcureAI includes several security controls:

1. A dedicated MongoDB user with read-only permissions.
2. Validation of AI-generated MongoDB aggregation queries.
3. Rejection of prohibited aggregation stages.
4. Environment variables for sensitive credentials.
5. MongoDB access restricted to localhost through Docker Compose.

These measures reduce risk but do not guarantee complete protection against every possible attack.

## Testing

The project includes several testing scripts:

```text
backend/quick_test.py
backend/test_readonly.py
backend/test_mongodb.py
backend/test_gemini.py
```

To run the automated question checks, start the backend and execute:

```powershell
python backend/quick_test.py
```

The automated question checks cover common procurement questions. Passing these checks does not guarantee that every AI-generated answer is accurate.

## Dataset

The development database contains **346,018 procurement records**.

The data is based on public procurement records and includes information about purchases, departments, suppliers, prices, and dates.

The CSV files are excluded from Git because of their size. They must be provided separately to reproduce the database.

## Limitations

- AI-generated answers may occasionally be inaccurate.
- Query generation depends on the availability of the Gemini API.
- MongoDB and the procurement dataset must be configured before use.
- The application is designed for local development and demonstration.
- Additional testing and security review would be required before production deployment.

## Project Purpose

ProcureAI was developed as an AI-powered procurement analysis project to demonstrate the integration of:

- Natural-language processing
- Large language models
- Database query generation
- Query validation
- Backend API development
- Frontend web development

The goal is to make procurement data easier to explore without requiring users to write database queries manually.
### Download Dataset

The procurement dataset is available on Google Drive:

[Download purchases_cleaned.csv](https://drive.google.com/file/d/1aD2y-5ooneDEWf6UY2WKeQ1lCPPZmRiH/view?usp=sharing)

Download the CSV file and place it in the `data` folder before running the import script.
