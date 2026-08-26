// ─── Auth ────────────────────────────────────────────────────────────────────
export type UserRole = 'admin' | 'officer' | 'analyst' | 'viewer' | 'company'
export type UserStatus = 'active' | 'inactive' | 'suspended'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  status: UserStatus
  department: string | null
  phone: string | null
  is_verified: boolean
  last_login: string | null
  company_id: string | null
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface LoginRequest {
  email: string
  password: string
}

// ─── Common ───────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// ─── Company ──────────────────────────────────────────────────────────────────
export type CompanyType = 'private_limited' | 'public_limited' | 'partnership' | 'sole_proprietorship' | 'llp' | 'other'
export type Industry =
  | 'manufacturing' | 'retail' | 'wholesale' | 'services' | 'technology'
  | 'healthcare' | 'construction' | 'real_estate' | 'agriculture'
  | 'financial' | 'hospitality' | 'transportation' | 'energy' | 'other'
export type CompanyStatus = 'active' | 'inactive' | 'under_review' | 'blacklisted'

export interface Company {
  id: string
  name: string
  registration_number: string
  tax_id: string | null
  gst_number: string | null
  company_type: CompanyType | null
  industry: Industry | null
  status: CompanyStatus
  incorporation_date: string | null
  country_of_incorporation: string
  registered_address: string
  city: string | null
  state: string | null
  postal_code: string | null
  contact_email: string
  contact_phone: string | null
  website: string | null
  annual_turnover: number | null
  number_of_employees: number | null
  notes: string | null
  application_count: number | null
  created_at: string
  updated_at: string
}

export interface CompanyCreate {
  name: string
  registration_number: string
  tax_id?: string
  gst_number?: string
  company_type?: CompanyType
  industry?: Industry
  incorporation_date?: string
  country_of_incorporation?: string
  registered_address: string
  city?: string
  state?: string
  contact_email: string
  contact_phone?: string
  annual_turnover?: number
  number_of_employees?: number
}

// ─── Application ─────────────────────────────────────────────────────────────
export type LoanPurpose =
  | 'working_capital' | 'capital_expenditure' | 'debt_refinancing'
  | 'expansion' | 'acquisition' | 'trade_finance' | 'other'
export type ApplicationStatus =
  | 'draft' | 'submitted' | 'under_review' | 'ocr_processing' | 'ocr_complete'
  | 'ratio_calculated' | 'rule_evaluated' | 'ml_predicted' | 'report_generated'
  | 'approved' | 'rejected' | 'manual_review' | 'withdrawn'
export type FinalDecision = 'pending' | 'approved' | 'rejected' | 'manual_review'

export interface PipelineStatus {
  ocr_completed: boolean
  ratios_calculated: boolean
  rules_evaluated: boolean
  ml_predicted: boolean
  report_generated: boolean
}

export interface Application {
  id: string
  application_number: string
  company_id: string
  company: Company
  loan_amount_requested: number
  loan_purpose: LoanPurpose
  loan_tenure_months: number
  interest_rate_requested: number | null
  collateral_description: string | null
  collateral_value: number | null
  status: ApplicationStatus
  pipeline: PipelineStatus
  final_decision: FinalDecision
  risk_score: number | null
  decision_reason: string | null
  officer_notes: string | null
  assigned_officer_id: string | null
  assigned_officer: string | null
  created_at: string
  updated_at: string
}

export interface ApplicationCreate {
  company_id: string
  loan_amount_requested: number
  loan_purpose: LoanPurpose
  loan_tenure_months: number
  interest_rate_requested?: number
  collateral_description?: string
  collateral_value?: number
}

export interface DashboardStats {
  total: number
  approved: number
  rejected: number
  manual_review: number
  pending: number
  draft: number
  submitted: number
  in_pipeline: number
  withdrawn: number
  approval_rate: number
  avg_risk_score: number
  total_loan_amount_approved: number
}

// ─── Document ─────────────────────────────────────────────────────────────────
export type DocumentType =
  | 'balance_sheet' | 'profit_loss' | 'cash_flow'
  | 'auditor_report' | 'gst_report' | 'bank_statement' | 'other'
export type DocumentStatus = 'uploaded' | 'processing' | 'extracted' | 'failed'

export interface Document {
  id: string
  application_id: string
  document_type: DocumentType
  original_filename: string
  file_size_bytes: number
  financial_year: number | null
  status: DocumentStatus
  ocr_processed: boolean
  created_at: string
  updated_at: string
}

// ─── OCR ─────────────────────────────────────────────────────────────────────
export interface OCRResult {
  id: string
  application_id: string
  document_id: string
  raw_text: string | null
  extracted_fields: Record<string, unknown>
  confidence_score: number | null
  processing_time_ms: number | null
  ocr_engine: string | null
  status: string
  error_message: string | null
  created_at: string
}

/** GET /ocr/application/{id} — fields merged across every document. */
export interface ApplicationOCRSummary {
  application_id: string
  total_documents: number
  extracted_documents: number
  failed_documents: number
  pending_documents: number
  combined_fields: Record<string, number | null>
  field_sources: Record<string, string>
  overall_confidence: number | null
  warnings: string[]
}

// ─── Financial Ratio ─────────────────────────────────────────────────────────
export type RiskLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high'
export type HealthSignal = 'positive' | 'neutral' | 'negative'
export type OverallHealth = 'excellent' | 'good' | 'fair' | 'poor' | 'critical'

export interface RatioDetail {
  name: string
  display_name: string
  value: number | null
  unit: string
  formula: string
  risk_level: RiskLevel
  health_signal: HealthSignal
  benchmark_min: number | null
  benchmark_max: number | null
  interpretation: string
}

export interface RatioSummary {
  overall_health: OverallHealth
  risk_distribution: Record<RiskLevel, number>
  positive_signals: number
  negative_signals: number
  neutral_signals: number
  total_ratios: number
}

export interface FinancialRatioResponse {
  application_id: string
  ratios: RatioDetail[]
  overall_health: OverallHealth | null
  calculated_at: string
}

// ─── Rule Engine ─────────────────────────────────────────────────────────────
export type RuleOperator = 'lt' | 'lte' | 'gt' | 'gte' | 'eq' | 'neq' | 'is_negative' | 'is_positive'
export type RuleCategory =
  | 'liquidity' | 'solvency' | 'profitability' | 'cash_flow'
  | 'leverage' | 'coverage' | 'qualitative' | 'regulatory'

export type RuleAction = 'reject' | 'manual_review' | 'flag'

export interface Rule {
  id: string
  name: string
  description: string | null
  category: RuleCategory
  metric_field: string
  operator: RuleOperator
  threshold: number | null
  action: RuleAction
  is_mandatory: boolean
  is_active: boolean
  priority: number
  failure_message: string | null
  pass_message: string | null
  industry: Industry | null
  extra_config: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface RuleCreate {
  name: string
  description?: string
  category: RuleCategory
  metric_field: string
  operator: RuleOperator
  threshold?: number
  action: RuleAction
  is_mandatory: boolean
  priority?: number
  failure_message?: string
  pass_message?: string
  industry?: Industry | null
}

export interface RuleResultItem {
  rule_id: string
  rule_name: string
  category: RuleCategory
  metric_field: string
  operator: RuleOperator
  threshold: number | null
  metric_value: number | null
  triggered: boolean
  is_mandatory: boolean
  action: RuleAction
  priority: number
  message: string
}

export type RuleEngineOutcome = 'pass' | 'reject' | 'manual_review'

export interface RuleEngineResponse {
  application_id: string
  overall_outcome: RuleEngineOutcome
  ml_should_run: boolean
  evaluated_at: string
  total_rules: number
  triggered_count: number
  mandatory_failures: string[]
  advisory_triggers: string[]
  passed_rules: string[]
  skipped_rules: string[]
  results: RuleResultItem[]
  rejection_reason: string | null
}

// ─── Prediction ───────────────────────────────────────────────────────────────
export type ModelName = 'logistic_regression' | 'random_forest' | 'xgboost' | 'ensemble'
export type PredictionOutcome = 'low_risk' | 'high_risk'

export interface ShapEntry {
  feature: string
  value: number
  direction: 'increases' | 'decreases'
}

export interface PredictionResponse {
  id: string
  application_id: string
  model_used: ModelName
  probability_of_default: number
  outcome: PredictionOutcome
  risk_score: number
  risk_level: RiskLevel
  shap_values: Record<string, number>
  feature_importance: Record<string, number>
  explanation_text: string | null
  recommendation: string | null
  ml_executed: boolean
  skip_reason: string | null
  model_metrics: Record<string, unknown>
  created_at: string
}

export interface ModelMetrics {
  accuracy: number
  precision: number
  recall: number
  f1: number
  roc_auc: number
  cv_roc_auc_mean: number
  cv_roc_auc_std: number
}

export interface ModelStatus {
  models_trained: boolean
  trained_at: string | null
  best_model: string | null
  best_roc_auc: number | null
  selected_feature_count: number | null
  total_training_samples: number | null
  model_metrics: Record<string, ModelMetrics> | null
}

export interface TrainingResponse {
  message: string
  models: Record<string, unknown>
  feature_count: number
  training_samples: number
}

// ─── Pipeline ────────────────────────────────────────────────────────────────

export interface StageResult {
  stage: string
  status: 'completed' | 'skipped' | 'failed'
  detail: string | null
  duration_seconds: number
}

export interface PipelineStageState {
  stage: string
  label: string
  complete: boolean
  can_run: boolean
  blocked_reason: string | null
}

export interface PipelineStatusResponse {
  application_id: string
  application_number: string
  status: string
  final_decision: string
  document_count: number
  documents_extracted: number
  stages: PipelineStageState[]
  next_stage: string | null
  is_complete: boolean
  can_run_pipeline: boolean
}

export interface PipelineRunResponse {
  application_id: string
  application_number: string
  started_at: string
  finished_at: string
  total_duration_seconds: number
  stages: StageResult[]
  completed_stages: number
  skipped_stages: number
  failed_stage: string | null
  final_status: string
  final_decision: string
  risk_score: number | null
  risk_level: string | null
  rule_outcome: string | null
  ml_executed: boolean
  report_id: string | null
  summary: string
}

export interface BatchPipelineItem {
  application_id: string
  application_number: string
  status: string
  detail: string | null
}

export interface BatchPipelineResponse {
  requested: number
  succeeded: number
  failed: number
  skipped: number
  items: BatchPipelineItem[]
  duration_seconds: number
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_applications: number
  total_approved: number
  total_rejected: number
  total_manual_review: number
  total_pending: number
  approval_rate: number
  avg_risk_score: number | null
  avg_loan_amount_requested: number | null
  total_loan_amount_approved: number
  avg_processing_days: number | null
  models_trained: boolean
}

export interface ApplicationTrend {
  date: string
  submitted: number
  approved: number
  rejected: number
}

export interface RiskDistribution {
  risk_level: string
  count: number
  percentage: number
}

export interface IndustryBreakdown {
  industry: string
  count: number
  total_loan_amount: number
  avg_risk_score: number | null
}

export interface LoanPurposeBreakdown {
  purpose: string
  count: number
  total_amount: number
  approval_rate: number
}

export interface PipelineFunnelStage {
  stage: string
  label: string
  count: number
  conversion_rate: number | null
}

export interface RuleTriggerStat {
  rule_id: string
  rule_name: string
  category: string
  trigger_count: number
  is_mandatory: boolean
}

export interface PipelineMetrics {
  stage_completion: Record<string, number>
  stage_conversion: Record<string, number | null>
  bottleneck_stage: string | null
}

// ─── Report ───────────────────────────────────────────────────────────────────
export type ReportStatus = 'generating' | 'complete' | 'failed'

export interface Report {
  id: string
  application_id: string
  status: ReportStatus
  filename: string
  file_path: string
  file_size_bytes: number | null
  version: number
  generated_by: string | null
  generation_error: string | null
  created_at: string
  updated_at: string
}
