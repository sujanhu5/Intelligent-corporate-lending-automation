-- =============================================================================
-- Corporate Lending Automation — PostgreSQL Schema
-- Run once against a freshly-created database:
--   psql -U postgres -d corporate_lending -f backend/database/schema.sql
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fuzzy company name search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- for JSONB GIN indexes

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'officer', 'viewer');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');

CREATE TYPE company_type AS ENUM (
    'private_limited', 'public_limited', 'partnership',
    'sole_proprietorship', 'llp', 'other'
);
CREATE TYPE company_status AS ENUM ('active', 'inactive', 'under_review', 'blacklisted');
CREATE TYPE industry AS ENUM (
    'manufacturing', 'retail', 'wholesale', 'services', 'technology',
    'healthcare', 'construction', 'real_estate', 'agriculture',
    'financial', 'hospitality', 'transportation', 'energy', 'other'
);

CREATE TYPE application_status AS ENUM (
    'draft', 'submitted', 'under_review', 'ocr_processing', 'ocr_complete',
    'ratio_calculated', 'rule_evaluated', 'ml_predicted', 'report_generated',
    'approved', 'rejected', 'manual_review', 'withdrawn'
);
CREATE TYPE loan_purpose AS ENUM (
    'working_capital', 'capital_expenditure', 'debt_refinancing',
    'expansion', 'acquisition', 'trade_finance', 'other'
);
CREATE TYPE final_decision AS ENUM ('approved', 'rejected', 'manual_review', 'pending');

CREATE TYPE document_type AS ENUM (
    'balance_sheet', 'profit_loss', 'cash_flow',
    'auditor_report', 'gst_report', 'bank_statement', 'other'
);
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'extracted', 'failed');

CREATE TYPE rule_category AS ENUM (
    'liquidity', 'solvency', 'profitability', 'cash_flow',
    'leverage', 'coverage', 'qualitative', 'regulatory'
);
CREATE TYPE rule_operator AS ENUM (
    'lt', 'lte', 'gt', 'gte', 'eq', 'neq', 'is_negative', 'is_positive'
);
CREATE TYPE rule_action AS ENUM ('reject', 'manual_review', 'flag');

CREATE TYPE model_used AS ENUM (
    'logistic_regression', 'random_forest', 'xgboost', 'ensemble'
);
CREATE TYPE prediction_outcome AS ENUM ('low_risk', 'high_risk');
CREATE TYPE risk_level AS ENUM ('very_low', 'low', 'medium', 'high', 'very_high');

CREATE TYPE report_status AS ENUM ('generating', 'complete', 'failed');

CREATE TYPE audit_action AS ENUM (
    'user_login', 'user_logout', 'user_created', 'user_updated', 'password_changed',
    'company_created', 'company_updated',
    'application_created', 'application_updated', 'application_submitted',
    'application_withdrawn', 'decision_made',
    'document_uploaded', 'document_deleted',
    'ocr_started', 'ocr_completed', 'ocr_failed',
    'ratios_calculated', 'rules_evaluated', 'ml_predicted',
    'report_generated', 'pipeline_completed',
    'rule_created', 'rule_updated', 'rule_deleted', 'model_trained'
);

-- =============================================================================
-- TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            user_role    NOT NULL DEFAULT 'analyst',
    status          user_status  NOT NULL DEFAULT 'active',
    department      VARCHAR(100),
    phone           VARCHAR(20),
    is_verified     BOOLEAN      NOT NULL DEFAULT FALSE,
    last_login      VARCHAR(50),
    profile_notes   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email  ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);

-- -----------------------------------------------------------------------------
-- companies
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                     VARCHAR(255)    NOT NULL,
    registration_number      VARCHAR(100)    NOT NULL UNIQUE,
    tax_id                   VARCHAR(50),
    gst_number               VARCHAR(50),
    company_type             company_type    NOT NULL,
    industry                 industry        NOT NULL,
    status                   company_status  NOT NULL DEFAULT 'active',
    incorporation_date       VARCHAR(20),
    country_of_incorporation VARCHAR(100)    NOT NULL DEFAULT 'India',
    registered_address       TEXT,
    city                     VARCHAR(100),
    state                    VARCHAR(100),
    postal_code              VARCHAR(20),
    contact_email            VARCHAR(255),
    contact_phone            VARCHAR(20),
    website                  VARCHAR(255),
    annual_turnover          NUMERIC(18,2),
    number_of_employees      INTEGER,
    notes                    TEXT,
    created_at               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_name   ON companies USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_companies_regnum ON companies (registration_number);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies (status);

-- -----------------------------------------------------------------------------
-- loan_applications
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loan_applications (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_number       VARCHAR(50)          NOT NULL UNIQUE,
    company_id               UUID                 NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    assigned_officer_id      UUID                 REFERENCES users(id) ON DELETE SET NULL,
    loan_amount_requested    NUMERIC(18,2)        NOT NULL,
    loan_purpose             loan_purpose         NOT NULL,
    loan_tenure_months       INTEGER              NOT NULL,
    interest_rate_requested  NUMERIC(6,4),
    collateral_description   TEXT,
    collateral_value         NUMERIC(18,2),
    status                   application_status   NOT NULL DEFAULT 'draft',
    ocr_completed            BOOLEAN              NOT NULL DEFAULT FALSE,
    ratios_calculated        BOOLEAN              NOT NULL DEFAULT FALSE,
    rules_evaluated          BOOLEAN              NOT NULL DEFAULT FALSE,
    ml_predicted             BOOLEAN              NOT NULL DEFAULT FALSE,
    report_generated         BOOLEAN              NOT NULL DEFAULT FALSE,
    final_decision           final_decision       NOT NULL DEFAULT 'pending',
    decision_reason          TEXT,
    officer_notes            TEXT,
    risk_score               NUMERIC(5,2),
    created_at               TIMESTAMPTZ          NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ          NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_company_id ON loan_applications (company_id);
CREATE INDEX IF NOT EXISTS idx_applications_status     ON loan_applications (status);
CREATE INDEX IF NOT EXISTS idx_applications_decision   ON loan_applications (final_decision);
CREATE INDEX IF NOT EXISTS idx_applications_number     ON loan_applications (application_number);

-- -----------------------------------------------------------------------------
-- documents
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id    UUID            NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    document_type     document_type   NOT NULL,
    status            document_status NOT NULL DEFAULT 'uploaded',
    original_filename VARCHAR(255)    NOT NULL,
    stored_filename   VARCHAR(255)    NOT NULL UNIQUE,
    file_path         VARCHAR(500)    NOT NULL,
    file_size_bytes   BIGINT          NOT NULL,
    mime_type         VARCHAR(100)    NOT NULL,
    checksum_sha256   VARCHAR(64),
    financial_year    VARCHAR(20),
    processing_error  TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_application_id  ON documents (application_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_type   ON documents (document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status          ON documents (status);

-- -----------------------------------------------------------------------------
-- ocr_data
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_data (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id          UUID         NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    raw_text             TEXT,
    confidence_score     FLOAT,
    page_count           INTEGER,
    extracted_fields     JSONB,
    extraction_metadata  JSONB,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocr_data_document_id       ON ocr_data (document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_data_extracted_fields  ON ocr_data USING GIN (extracted_fields);

-- -----------------------------------------------------------------------------
-- financial_ratios
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_ratios (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id        UUID        NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    financial_year        VARCHAR(20),
    extracted_financials  JSONB,
    ratios                JSONB,
    overall_health        VARCHAR(50),
    health_notes          TEXT,
    calculation_metadata  JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_ratios_application_id ON financial_ratios (application_id);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_ratios          ON financial_ratios USING GIN (ratios);

-- -----------------------------------------------------------------------------
-- rules
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200)    NOT NULL UNIQUE,
    description     TEXT,
    category        rule_category   NOT NULL,
    metric_field    VARCHAR(100)    NOT NULL,
    operator        rule_operator   NOT NULL,
    threshold       NUMERIC(18,6),
    action          rule_action     NOT NULL,
    is_mandatory    BOOLEAN         NOT NULL DEFAULT TRUE,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    priority        INTEGER         NOT NULL DEFAULT 100,
    failure_message TEXT,
    pass_message    TEXT,
    extra_config    JSONB,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_is_active  ON rules (is_active);
CREATE INDEX IF NOT EXISTS idx_rules_priority   ON rules (priority);
CREATE INDEX IF NOT EXISTS idx_rules_category   ON rules (category);

-- -----------------------------------------------------------------------------
-- predictions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id          UUID              NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    model_used              model_used        NOT NULL,
    model_version           VARCHAR(50),
    probability_of_default  NUMERIC(8,6)      NOT NULL,
    outcome                 prediction_outcome NOT NULL,
    risk_score              NUMERIC(5,2)       NOT NULL,
    risk_level              risk_level         NOT NULL,
    shap_values             JSONB,
    feature_importance      JSONB,
    explanation_text        TEXT,
    input_features          JSONB,
    model_metrics           JSONB,
    recommendation          TEXT,
    ml_executed             BOOLEAN            NOT NULL DEFAULT TRUE,
    skip_reason             TEXT,
    created_at              TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_application_id ON predictions (application_id);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_level     ON predictions (risk_level);

-- -----------------------------------------------------------------------------
-- reports
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id   UUID           NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    status           report_status  NOT NULL DEFAULT 'generating',
    filename         VARCHAR(255)   NOT NULL UNIQUE,
    file_path        VARCHAR(500)   NOT NULL,
    file_size_bytes  BIGINT,
    version          INTEGER        NOT NULL DEFAULT 1,
    generated_by     VARCHAR(255),
    generation_error TEXT,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_application_id ON reports (application_id);

-- -----------------------------------------------------------------------------
-- audit_logs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID         REFERENCES users(id) ON DELETE SET NULL,
    entity_type  VARCHAR(50),
    entity_id    VARCHAR(50),
    action       audit_action NOT NULL,
    description  TEXT         NOT NULL,
    old_values   JSONB,
    new_values   JSONB,
    ip_address   VARCHAR(45),
    user_agent   TEXT,
    request_id   VARCHAR(50),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id     ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity      ON audit_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action      ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at  ON audit_logs (created_at DESC);

-- =============================================================================
-- AUTOMATIC updated_at trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'companies', 'loan_applications', 'documents',
        'ocr_data', 'financial_ratios', 'rules', 'predictions', 'reports', 'audit_logs'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_updated_at ON %I;
             CREATE TRIGGER trg_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at();',
            t, t
        );
    END LOOP;
END;
$$;

-- =============================================================================
-- SEED DATA — default admin user and banking rules
-- =============================================================================

-- Default admin user (password: Admin@123 — change immediately in production)
-- Hash generated with: passlib.context.CryptContext(['bcrypt']).hash('Admin@123')
INSERT INTO users (id, email, full_name, hashed_password, role, status, is_verified)
VALUES (
    uuid_generate_v4(),
    'admin@corporatelending.com',
    'System Administrator',
    '$2b$12$HE.LiWTOgg8/unLeQSFSg.rgV3gWTxNHsU2EdWrgl6lpmBTbjXBKu',
    'admin',
    'active',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Default banking rules (ordered by priority)
INSERT INTO rules (name, description, category, metric_field, operator, threshold, action, is_mandatory, priority, failure_message, pass_message)
VALUES
-- Liquidity rules
(
    'Minimum Current Ratio',
    'Current ratio below 1.0 indicates the company cannot meet short-term obligations.',
    'liquidity', 'current_ratio', 'lt', 1.0, 'reject', TRUE, 10,
    'Current Ratio is below the minimum threshold of 1.0. The company lacks sufficient liquidity to meet short-term obligations.',
    'Current Ratio is adequate. Short-term liquidity is acceptable.'
),
(
    'Quick Ratio Floor',
    'Quick ratio below 0.5 signals severe liquidity stress.',
    'liquidity', 'quick_ratio', 'lt', 0.5, 'reject', TRUE, 20,
    'Quick Ratio is critically low (below 0.5), indicating severe short-term liquidity risk.',
    'Quick Ratio is within acceptable range.'
),
-- Leverage rules
(
    'Maximum Debt-Equity Ratio',
    'High D/E ratio signals excessive leverage.',
    'leverage', 'debt_equity_ratio', 'gt', 2.5, 'reject', TRUE, 30,
    'Debt-to-Equity Ratio exceeds 2.5. The company carries excessive financial leverage.',
    'Debt-to-Equity Ratio is within acceptable leverage limits.'
),
(
    'Maximum Debt Ratio',
    'Debt ratio above 0.8 indicates over-reliance on debt financing.',
    'leverage', 'debt_ratio', 'gt', 0.8, 'manual_review', FALSE, 40,
    'Debt Ratio exceeds 0.8. High proportion of assets financed by debt requires manual review.',
    'Debt Ratio is within acceptable range.'
),
-- Profitability rules
(
    'Positive Return on Assets',
    'Negative ROA means the company is losing money on its asset base.',
    'profitability', 'return_on_assets', 'is_negative', NULL, 'reject', TRUE, 50,
    'Return on Assets is negative. The company is not generating profit from its assets.',
    'Return on Assets is positive, indicating profitable asset utilisation.'
),
(
    'Minimum Return on Equity',
    'ROE below 5% is insufficient for institutional lending.',
    'profitability', 'return_on_equity', 'lt', 5.0, 'manual_review', FALSE, 60,
    'Return on Equity is below 5%. Shareholder returns are inadequate for the requested credit level.',
    'Return on Equity meets minimum profitability standards.'
),
(
    'Positive Net Profit Margin',
    'Negative net profit margin indicates the company is loss-making.',
    'profitability', 'net_profit_margin', 'is_negative', NULL, 'reject', TRUE, 70,
    'Net Profit Margin is negative. The company is operating at a net loss.',
    'Net Profit Margin is positive.'
),
-- Coverage rules
(
    'Minimum Interest Coverage Ratio',
    'ICR below 1.5 means earnings may not cover interest payments.',
    'coverage', 'interest_coverage_ratio', 'lt', 1.5, 'reject', TRUE, 80,
    'Interest Coverage Ratio is below 1.5. Earnings do not adequately cover interest expense.',
    'Interest Coverage Ratio is adequate. Debt servicing capacity is satisfactory.'
),
(
    'Minimum Debt Service Coverage Ratio',
    'DSCR below 1.2 indicates insufficient cash flow to service total debt.',
    'coverage', 'debt_service_coverage_ratio', 'lt', 1.2, 'reject', TRUE, 90,
    'Debt Service Coverage Ratio is below 1.2. Cash flow is insufficient to cover total debt obligations.',
    'Debt Service Coverage Ratio indicates adequate cash flow for debt servicing.'
),
-- Cash flow rules
(
    'Positive Operating Cash Flow',
    'Negative operating cash flow is a critical red flag.',
    'cash_flow', 'operating_cash_flow_ratio', 'is_negative', NULL, 'reject', TRUE, 100,
    'Operating Cash Flow is negative. The company''s core operations are not generating positive cash flow.',
    'Operating Cash Flow is positive, indicating healthy core business performance.'
),
-- Solvency rules
(
    'Positive Net Worth',
    'Negative net worth (equity) indicates technical insolvency.',
    'solvency', 'financial_leverage', 'gt', 10.0, 'reject', TRUE, 110,
    'Financial Leverage is extremely high, indicating potential insolvency risk.',
    'Financial Leverage is within manageable limits.'
)
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- VIEWS (for analytics dashboard)
-- =============================================================================

CREATE OR REPLACE VIEW v_application_summary AS
SELECT
    la.id,
    la.application_number,
    la.status,
    la.final_decision,
    la.risk_score,
    la.loan_amount_requested,
    la.created_at,
    la.updated_at,
    c.name              AS company_name,
    c.industry,
    c.company_type,
    u.full_name         AS officer_name,
    p.probability_of_default,
    p.risk_level,
    p.outcome           AS ml_outcome
FROM loan_applications la
LEFT JOIN companies    c ON c.id = la.company_id
LEFT JOIN users        u ON u.id = la.assigned_officer_id
LEFT JOIN LATERAL (
    SELECT probability_of_default, risk_level, outcome
    FROM predictions
    WHERE application_id = la.id
    ORDER BY created_at DESC
    LIMIT 1
) p ON TRUE;

CREATE OR REPLACE VIEW v_monthly_stats AS
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*)                         AS total_applications,
    COUNT(*) FILTER (WHERE final_decision = 'approved')      AS approved,
    COUNT(*) FILTER (WHERE final_decision = 'rejected')      AS rejected,
    COUNT(*) FILTER (WHERE final_decision = 'manual_review') AS manual_review,
    COUNT(*) FILTER (WHERE final_decision = 'pending')       AS pending,
    AVG(risk_score)                                          AS avg_risk_score,
    SUM(loan_amount_requested)                               AS total_loan_amount
FROM loan_applications
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;
