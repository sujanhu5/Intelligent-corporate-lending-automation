# Corporate Lending Automation (CLA)

**Intelligent Corporate Lending Automation — Rule-Based Decision Systems and Machine Learning for Credit Risk Assessment**

A full-stack enterprise platform that automates the corporate loan underwriting pipeline: from document intake and OCR extraction, through financial ratio computation and rule-based policy evaluation, to machine-learning-driven credit risk scoring and automated PDF report generation.

Built as a Final Year Engineering Project (FYP).

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI 0.104 · SQLAlchemy 2.0 · PostgreSQL 16 · Celery + Redis |
| **Frontend** | React 18 · Vite 5 · TypeScript · TailwindCSS · Recharts · Zustand |
| **ML** | scikit-learn · XGBoost · SHAP · SMOTE (imbalanced-learn) |
| **OCR** | PyMuPDF (primary) · Tesseract (fallback) |
| **Reports** | ReportLab — 6-page PDF credit assessment reports |
| **Auth** | JWT + bcrypt · Role-Based Access Control (admin / officer / analyst / viewer) |
| **DevOps** | Docker Compose · GitHub Actions CI · Alembic migrations |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React SPA (Vite)                        │
│   Landing · Login · Dashboard · Applications · Companies       │
│   Rule Engine · ML Models · Analytics · Pipeline · Settings     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ OCR      │ │ Ratios   │ │ Rules    │ │ ML       │           │
│  │ Engine   │→│ Calculator│→│ Engine   │→│ Predictor│→ Reports  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   PostgreSQL 16 (JSONB) │
              └─────────────────────────┘
```

### Pipeline Flow (6 Stages)

**Submit → OCR → Ratios → Rules → ML → Report → Decision**

1. **Submit** — Loan officer uploads financial documents (PDF)
2. **OCR** — PyMuPDF extracts text and tables; Tesseract fallback
3. **Ratios** — 20+ financial ratios computed (liquidity, leverage, coverage, profitability)
4. **Rules** — 11 banking rules evaluated; mandatory breaches auto-reject before ML
5. **ML** — Random Forest / XGBoost / Logistic Regression predict default probability
6. **Report** — 6-page ReportLab PDF generated with ratios, rules, risk score, recommendation

---

## ML Model Performance

Trained on the **Taiwanese Corporate Bankruptcy Prediction** dataset (6,819 companies, 96 features → top 30 selected via mutual information).

| Model | ROC-AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| **Random Forest** | **0.9495** | 0.9698 | 0.7241 | 0.2692 | 0.3925 |
| XGBoost | 0.9372 | 0.9662 | 0.6774 | 0.2692 | 0.3853 |
| Logistic Regression | 0.9339 | 0.9603 | 0.5676 | 0.2692 | 0.3652 |

- SMOTE-balanced training for minority class
- 5-fold stratified cross-validation (CV mean AUC: 0.996)
- SHAP feature attributions on every prediction for explainability
- Composite 0–100 risk score with clear risk bands

---

## Rule Engine

11 configurable banking rules split into:

- **Mandatory** (7) — failure immediately rejects; ML is skipped
  - Current Ratio ≥ 1.0, Quick Ratio ≥ 0.5, Debt-Equity ≤ 2.5
  - ROA > 0, Net Profit Margin > 0
  - Interest Coverage ≥ 1.5, DSCR ≥ 1.2

- **Advisory** (4) — failure flags manual review; ML still runs
  - Operating Margin ≥ 5%, Gross Profit Margin ≥ 10%
  - Debt Ratio ≤ 70%, Cash Flow Ratio ≥ 0.5

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis (optional — only for Celery background jobs)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd Coorporate_lending_automation
cp .env.example .env
# Edit .env → set DATABASE_URL to your PostgreSQL connection string
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cd ..

# Create database
psql -U postgres -c "CREATE DATABASE corporate_lending;"

# Start server (from backend/ directory)
cd backend
uvicorn app.main:app --reload --port 8000
```

The first run auto-creates all tables and seeds a default admin user:
- **Email:** `admin@corporatelending.com`
- **Password:** `Admin@1234`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — you'll see the landing page.

### 4. (Optional) Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, the backend, a Celery worker, and the Nginx-fronted frontend. Access at http://localhost.

---

## Database Migrations

```bash
cd backend

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Running Tests

```bash
cd backend

# Create the test database first
psql -U postgres -c "CREATE DATABASE corporate_lending_test;"

# Run all tests
pytest

# With coverage
pytest --cov=app --cov=rules --cov=ml --cov-report=html
```

---

## Training the ML Models

```bash
cd backend
python -m training --dataset ../datasets/company_bankruptcy_prediction.csv --out ../models

# Options
python -m training --dry-run          # preview without saving
python -m training --no-smote         # skip SMOTE balancing
python -m training --models rf xgb    # train specific models only
python -m training --top-k 20         # top 20 features instead of 30
```

---

## API Documentation

When running in development mode, interactive API docs are available:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | JWT authentication |
| GET/POST | `/api/v1/companies` | Company CRUD |
| GET/POST | `/api/v1/applications` | Application CRUD |
| POST | `/api/v1/documents/{id}/upload` | Document upload |
| POST | `/api/v1/ocr/{id}/extract` | Run OCR extraction |
| POST | `/api/v1/ratios/{id}/calculate` | Calculate financial ratios |
| GET/POST | `/api/v1/rules` | Rule CRUD |
| POST | `/api/v1/predictions/{id}/predict` | Run ML prediction |
| POST | `/api/v1/reports/{id}/generate` | Generate PDF report |
| POST | `/api/v1/pipeline/run/{id}` | Run full pipeline |
| GET | `/api/v1/analytics/summary` | Dashboard analytics |

---

## Project Structure

```
Coorporate_lending_automation/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI route handlers
│   │   ├── core/            # Security, middleware, logging
│   │   ├── database/        # SQLAlchemy engine, session, base
│   │   ├── models/          # ORM models (User, Company, Application, etc.)
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── utils/           # File handling, validators
│   │   ├── config.py        # Environment configuration
│   │   └── main.py          # FastAPI app entry point
│   ├── ml/                  # ML training, prediction, risk scoring
│   ├── ocr/                 # Document OCR extraction
│   ├── ratios/              # Financial ratio computation
│   ├── rules/               # Rule engine evaluator
│   ├── reports/             # PDF report generation
│   ├── training/            # CLI model training tool
│   ├── workers/             # Celery background tasks
│   ├── tests/               # pytest test suite
│   └── alembic/             # Database migration scripts
├── frontend/
│   └── src/
│       ├── api/             # Typed API client functions
│       ├── components/      # Reusable UI components
│       ├── lib/             # Theme, utilities
│       ├── pages/           # Page components
│       ├── store/           # Zustand auth store
│       └── types/           # TypeScript type definitions
├── config/                  # ML feature configuration
├── datasets/                # Training dataset (CSV)
├── models/                  # Trained model artifacts (.pkl)
├── docker-compose.yml       # Multi-service orchestration
├── Dockerfile.backend       # Backend container
├── Dockerfile.frontend      # Frontend container (Nginx)
└── .github/workflows/ci.yml # CI pipeline
```

---

## Design System

The UI follows a **Digitomics-inspired design language:**

- **Palette:** Coral-orange primary (#EF6C1A), warm canvas backgrounds
- **Typography:** JetBrains Mono (headings, data) + Inter (body text)
- **Components:** Gradient pill buttons, rounded cards, blueprint grid backdrop
- **Theming:** Full light/dark mode with localStorage persistence

---

## License

This project is developed as a Final Year Engineering Project for academic purposes.
