# Incident Management Agent
### AI-Assisted Root Cause Analysis Platform

---

## 1. Project Overview

The **Incident Management Agent** is an AI-powered platform developed to assist engineering and operations teams in identifying, analyzing, and documenting the root causes of production incidents.

Modern IT environments generate large volumes of operational data — including logs, deployment changes, monitoring alerts, and incident reports. Analyzing this information manually during high-pressure incidents is often time-consuming and error-prone.

The primary objective of this project is to automate and accelerate the Root Cause Analysis (RCA) process by combining machine learning, semantic search, and Large Language Models (LLMs).

The system enables engineers to submit incident details, logs, timelines, and deployment changes. The platform then performs intelligent analysis to:

- Classify the incident category
- Predict incident severity
- Retrieve similar historical incidents
- Identify likely root causes
- Generate resolution recommendations
- Produce a structured Root Cause Analysis report

The generated RCA report provides engineering teams with a clear explanation of what happened, why it happened, how it was resolved, and what preventative measures should be implemented to avoid future occurrences.

---

## 2. Architecture Overview

The architecture is designed around a single core objective:

> **Automated Root Cause Analysis of Production Incidents**

Every major component in the system contributes toward generating accurate RCA documentation and assisting engineers during incident investigations.

### Core Technologies

| Component | Purpose |
|---|---|
| FastAPI | Backend API and business logic |
| PostgreSQL | Incident and RCA data storage |
| XGBoost | Severity and category prediction |
| Sentence Transformers | Semantic understanding of incidents |
| FAISS | Similar incident retrieval |
| Groq Llama | RCA generation and recommendations |
| HTML/CSS/JavaScript | User interface |

---

## 3. High-Level Architecture

```
Engineer / Administrator
            │
            ▼
     Web Application
(HTML, CSS, JavaScript)
            │
            ▼
        FastAPI API
            │
 ┌──────────┼──────────┐
 │          │          │
 ▼          ▼          ▼
Incident   AI      Reporting
Manager   Engine    Engine
 │          │          │
 └──────┬───┴──────┬───┘
        ▼          ▼
   PostgreSQL    FAISS
    Database   Knowledge Base
                  │
                  ▼
         Similar Incidents
                  │
                  ▼
           Groq Llama LLM
                  │
                  ▼
       Root Cause Analysis
            Generation
```

---

## 4. RCA Processing Pipeline

### Step 1 – Incident Submission

The engineer provides:
- Incident title
- Incident description
- Timeline of events
- System logs
- Deployment changes (Git Diff)

These inputs become the foundation for the RCA analysis.

### Step 2 – Incident Understanding

The system processes the submitted information and extracts meaningful operational indicators, such as:
- Error patterns
- Authentication failures
- Database issues
- Deployment failures
- Infrastructure anomalies
- Security events

### Step 3 – AI Classification

Machine learning models perform:

**Severity Prediction** — predicts one of: `Low` | `Medium` | `High` | `Critical`

**Category Classification** — identifies the incident domain: `Database` | `Infrastructure` | `Network` | `Security` | `Application` | `Deployment` | `Authentication` | `Storage` | `Monitoring`

These predictions provide context for RCA generation.

### Step 4 – Historical Incident Retrieval

The system searches the historical incident knowledge base using Sentence Embeddings and FAISS Vector Search to identify incidents with similar symptoms, causes, or resolution patterns. This historical context significantly improves RCA quality.

### Step 5 – Root Cause Inference

Using the current incident information, historical incident matches, and classification results, the AI engine determines:
- Probable root cause
- Contributing factors
- Business impact
- Resolution actions

### Step 6 – RCA Report Generation

The Groq-hosted Llama model generates a structured RCA document containing:

| Section | Description |
|---|---|
| Executive Summary | High-level overview of the incident |
| Business Impact | Explanation of affected systems and users |
| Incident Timeline | Chronological sequence of events |
| Evidence Collected | Supporting logs, deployment changes, and system observations |
| Root Cause | Detailed explanation of the underlying issue |
| Contributing Factors | Secondary conditions that worsened the incident |
| Resolution Actions | Steps taken to restore service |
| Preventive Measures | Recommendations to prevent recurrence |

---

## 5. Setup Instructions

### Prerequisites

Ensure the following software is installed before running the application:

**Required Software**
- Python 3.10+
- Node.js (v18+) and npm
- PostgreSQL 15+
- Git
- Modern web browser (Chrome, Edge, Firefox)

**AI Requirements**
- Groq API Key (Primary LLM)
- Gemini API Key (Optional Fallback)
- Internet connectivity (for pulling HuggingFace SentenceTransformer models)

### Clone the Repository

```bash
git clone <repository-url>
cd incident-management-agent
```

### Create Python Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

```bash
cd node_backend
npm install
cd ..
```

### Configure Environment Variables

Create a `.env` file inside the root project directory (`incident-management-agent/.env`):

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/incident_agent_db
JWT_SECRET=your-secret-key-32-chars-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
LLM_PROVIDER=groq
MOCK_AI_FALLBACK=true
```

### Database Setup

Create the PostgreSQL database:

```sql
CREATE DATABASE incident_agent_db;
```

Run the database initialization script:

```bash
python backend/init_db.py
```

### Train Machine Learning Models & FAISS Knowledge Base

Both the XGBoost Categorization/Severity models and the FAISS Semantic Index are built via a unified pipeline:

```bash
python backend/train_models.py
```

Generated model files (saved in `backend/models/`):
- `severity_clf.joblib`
- `category_clf.joblib`
- `sev_encoder.joblib`
- `cat_encoder.joblib`
- `faiss_index.bin`
- `historical_ids.joblib`

---

## 6. Run Instructions

### 1. Start PostgreSQL

Ensure the PostgreSQL service is running locally.

### 2. Start the Node.js API Gateway & Frontend

```bash
cd node_backend
node server.js
```

Expected output: `Node.js API Gateway & Frontend Server running on http://127.0.0.1:8000`

### 3. Start the Python AI Engine

Open a separate terminal, activate your virtual environment, and run:

```bash
cd backend
python -m uvicorn app.main:app --port 8001
```

Expected output: `Uvicorn running on http://127.0.0.1:8001`

### Access the Application

Open your browser and navigate to: **http://localhost:8000**

**API Documentation** (Swagger/ReDoc available on port 8001):
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Login Credentials

The application uses dynamic JWT authentication. Navigate to the **Registration Page** via the browser and create a new account to log in.

---

## 7. RCA Workflow

The platform follows a six-stage RCA workflow:

**Stage 1 — Incident Submission**
Engineers provide: Incident Title, Description, Timeline, Log Data, and Git Changes.

**Stage 2 — AI Classification**
The system predicts Severity Level and Incident Category using trained XGBoost models.

**Stage 3 — Similar Incident Retrieval**
FAISS performs dense semantic similarity search against historical incidents to reuse organizational knowledge, identify recurring patterns, and improve RCA context accuracy.

**Stage 4 — Root Cause Analysis**
The AI engine (powered by Llama-3 70B via Groq) analyzes current incident data, historical FAISS matches, logs, timelines, and deployment changes to determine probable underlying causes.

**Stage 5 — Resolution Recommendation**
The system dynamically generates diagnostic steps, recovery procedures, validation steps, and preventive actions.

**Stage 6 — RCA Report Generation**
A structured RCA report is automatically produced and permanently stored in the database for stakeholder review, auditing, and post-incident documentation.

---

## 8. Assumptions

**Historical Incident Knowledge Improves RCA Quality**
The platform assumes that the availability of historical incidents improves the quality and accuracy of generated RCA reports.

**Accurate Incident Inputs**
The system assumes that engineers provide sufficient logs, timelines, and deployment information during incident creation.

**AI as an Assistance Tool**
The generated RCA should be treated as an engineering aid and not as a replacement for human expertise.

---

## 9. Limitations

**Historical Incident Availability**
The similarity retrieval component performs best when a diverse set of historical incidents exists within the knowledge base. Limited incident history may reduce contextual understanding.

**Synthetic Model Training Data**
The machine learning models currently rely on synthetic incident datasets for training. In enterprise environments, model performance can be further improved using real operational incident records.

**AI-Generated RCA Validation**
Although the platform generates detailed RCA reports automatically, final RCA documentation should always be reviewed and validated by engineering teams before operational use.
