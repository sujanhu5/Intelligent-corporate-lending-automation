import { useEffect, useState, useRef } from 'react'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

interface SectionInfo {
  section_type: string
  document_id: string
  page_range: string
  fields_extracted: number
  confidence: number
  title_found: string
  variant: string
}

interface AnalysisResult {
  document_id: string
  total_pages: number
  sections_detected: number
  analysis_method: string
  company_name: string | null
  financial_year: string | null
  unit_context: string | null
  overall_confidence: number
  has_all_statements: boolean
  total_fields_extracted: number
  warnings: string[]
  sections: SectionInfo[]
}

interface ReportStatus {
  document_id: string
  status: string
  original_filename: string
  total_pages: number | null
  analysis_method: string | null
  company_name: string | null
  financial_year: string | null
  unit_context: string | null
  toc_found: boolean
  sections: {
    id: string
    section_type: string
    page_range: string
    status: string
    fields_extracted: number
    confidence: number
    title: string
    variant: string
  }[]
  warnings: string[]
}

const STATUS_BADGE: Record<string, string> = {
  uploaded: 'bg-blue-100 text-blue-800',
  processing: 'bg-amber-100 text-amber-800',
  extracted: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

const SECTION_LABELS: Record<string, string> = {
  balance_sheet: 'Balance Sheet',
  profit_loss: 'Profit & Loss',
  cash_flow: 'Cash Flow',
}

const SECTION_ICONS: Record<string, JSX.Element> = {
  balance_sheet: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  ),
  profit_loss: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2 20h.01M7 20v-4m5 4v-8m5 4v-2m5 2v-6" />
    </svg>
  ),
  cash_flow: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
}

export default function PortalAnnualReport() {
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [financialYear, setFinancialYear] = useState('')
  const [applicationId, setApplicationId] = useState('')
  const [applications, setApplications] = useState<{ id: string; application_number: string }[]>([])
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [reportStatus, setReportStatus] = useState<ReportStatus | null>(null)
  const [previousReports, setPreviousReports] = useState<any[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const { success, error } = useToast()

  useEffect(() => {
    portalApi.applications(1, 100).then(data => {
      setApplications(data.items.map((a: any) => ({ id: a.id, application_number: a.application_number })))
      if (data.items.length > 0) setApplicationId(data.items[0].id)
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    // Load previous annual report documents
    portalApi.documents().then(data => {
      const annuals = data.documents.filter((d: any) => d.document_type === 'annual_report')
      setPreviousReports(annuals)
    })
  }, [analysisResult])

  const handleUpload = async () => {
    if (!selectedFile || !applicationId) return
    setUploading(true)
    try {
      const result = await portalApi.uploadAnnualReport(applicationId, selectedFile, financialYear || undefined)
      success('Annual report uploaded successfully.')
      setUploadedDocId(result.id)
      setSelectedFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      error(extractError(err))
    } finally {
      setUploading(false)
    }
  }

  const handleAnalyze = async () => {
    if (!uploadedDocId) return
    setAnalyzing(true)
    try {
      const result = await portalApi.analyzeAnnualReport(uploadedDocId)
      setAnalysisResult(result)
      success(`Analysis complete: ${result.sections_detected} financial statement(s) detected.`)
    } catch (err) {
      error(extractError(err))
    } finally {
      setAnalyzing(false)
    }
  }

  const handleViewStatus = async (docId: string) => {
    try {
      const status = await portalApi.annualReportStatus(docId)
      setReportStatus(status)
    } catch (err) {
      error(extractError(err))
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
    } else {
      error('Only PDF files are accepted.')
    }
  }

  const formatSize = (bytes: number | null) => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const confidenceColor = (c: number) => {
    if (c >= 0.8) return 'text-green-600'
    if (c >= 0.5) return 'text-amber-600'
    return 'text-red-600'
  }

  const confidenceBar = (c: number) => {
    const pct = Math.round(c * 100)
    const bg = c >= 0.8 ? 'bg-green-500' : c >= 0.5 ? 'bg-amber-500' : 'bg-red-500'
    return (
      <div className="flex items-center gap-2">
        <div className="w-20 h-1.5 rounded-full bg-surface-2 overflow-hidden">
          <div className={`h-full rounded-full ${bg}`} style={{ width: `${pct}%` }} />
        </div>
        <span className={`text-xs font-mono font-bold ${confidenceColor(c)}`}>{pct}%</span>
      </div>
    )
  }

  if (loading) return <PageLoader />

  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary font-mono mb-2">Annual Report</div>
        <h1 className="text-h2 text-ink-primary">Annual Report Processing</h1>
        <p className="text-small text-ink-secondary mt-1">
          Upload your complete annual report and the system will automatically detect Balance Sheet,
          Profit & Loss, and Cash Flow statements.
        </p>
      </div>

      {/* How it works */}
      <div className="card p-5 mb-6 border border-border-subtle">
        <h3 className="text-xs font-bold text-ink-primary font-mono mb-3">How It Works</h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[
            { step: '1', title: 'Upload', desc: 'Upload your complete annual report PDF (up to 100 MB)' },
            { step: '2', title: 'Analyze', desc: 'System detects financial statement sections automatically' },
            { step: '3', title: 'Extract', desc: 'Financial data is extracted from detected sections' },
            { step: '4', title: 'Process', desc: 'Data flows through ratios, rules, ML, and report generation' },
          ].map(s => (
            <div key={s.step} className="flex gap-3">
              <div className="w-7 h-7 rounded-lg gradient-orange flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs font-bold font-mono">{s.step}</span>
              </div>
              <div>
                <div className="text-xs font-bold text-ink-primary">{s.title}</div>
                <div className="text-[11px] text-ink-secondary mt-0.5">{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Upload section */}
      {!uploadedDocId && !analysisResult && (
        <div className="card p-6 mb-6 border-2 border-primary/20">
          <h2 className="text-sm font-bold text-ink-primary font-mono mb-4">Upload Annual Report</h2>

          {applications.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-sm text-ink-secondary">No applications found. An annual report must be uploaded against a loan application.</p>
              <p className="text-xs text-ink-muted mt-1">Contact the bank to have an application created for your company.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">Application</label>
                  <select value={applicationId} onChange={e => setApplicationId(e.target.value)} className="input">
                    {applications.map(a => (
                      <option key={a.id} value={a.id}>{a.application_number}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Financial Year (optional)</label>
                  <input
                    type="text"
                    value={financialYear}
                    onChange={e => setFinancialYear(e.target.value)}
                    placeholder="e.g. FY2024-25"
                    className="input"
                  />
                </div>
              </div>

              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-border-default rounded-xl p-10 text-center cursor-pointer
                  hover:border-primary hover:bg-cr-50 transition-colors"
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf"
                  onChange={e => { const f = e.target.files?.[0]; if (f) setSelectedFile(f) }}
                  className="hidden"
                />
                <div className="w-14 h-14 rounded-xl gradient-orange flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-bold text-ink-primary">{selectedFile.name}</p>
                    <p className="text-xs text-ink-muted mt-1">{formatSize(selectedFile.size)} — Click to change</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-bold text-ink-primary">Drop your annual report PDF here</p>
                    <p className="text-xs text-ink-muted mt-1">Accepted: PDF files up to 100 MB (300-500+ pages supported)</p>
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <button onClick={handleUpload} disabled={!selectedFile || uploading} className="btn btn-primary">
                  {uploading ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Uploading...
                    </span>
                  ) : 'Upload Annual Report'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Analyze step */}
      {uploadedDocId && !analysisResult && (
        <div className="card p-6 mb-6 border-2 border-green-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-bold text-ink-primary">Annual Report Uploaded</h2>
              <p className="text-xs text-ink-secondary">Click "Analyze" to detect financial statement sections.</p>
            </div>
          </div>

          <button onClick={handleAnalyze} disabled={analyzing} className="btn btn-primary w-full">
            {analyzing ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Analyzing report... This may take a few minutes for large PDFs.
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Analyze Annual Report
              </span>
            )}
          </button>
        </div>
      )}

      {/* Analysis Results */}
      {analysisResult && (
        <div className="space-y-4 mb-6">
          {/* Summary Card */}
          <div className="card p-5 border border-border-subtle">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-ink-primary font-mono">Analysis Complete</h2>
                {analysisResult.company_name && (
                  <p className="text-xs text-ink-secondary mt-0.5">{analysisResult.company_name}</p>
                )}
              </div>
              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide
                ${analysisResult.has_all_statements ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
                {analysisResult.has_all_statements ? 'All Statements Found' : 'Partial'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-ink-primary font-mono">{analysisResult.total_pages}</div>
                <div className="text-[10px] text-ink-muted uppercase tracking-wide">Total Pages</div>
              </div>
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-primary font-mono">{analysisResult.sections_detected}</div>
                <div className="text-[10px] text-ink-muted uppercase tracking-wide">Sections Found</div>
              </div>
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-ink-primary font-mono">{analysisResult.total_fields_extracted}</div>
                <div className="text-[10px] text-ink-muted uppercase tracking-wide">Fields Extracted</div>
              </div>
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className={`text-lg font-bold font-mono ${confidenceColor(analysisResult.overall_confidence)}`}>
                  {Math.round(analysisResult.overall_confidence * 100)}%
                </div>
                <div className="text-[10px] text-ink-muted uppercase tracking-wide">Confidence</div>
              </div>
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-xs font-bold text-ink-primary font-mono">{analysisResult.analysis_method === 'toc_based' ? 'TOC' : 'Keyword'}</div>
                <div className="text-[10px] text-ink-muted uppercase tracking-wide">Method</div>
              </div>
            </div>

            {(analysisResult.financial_year || analysisResult.unit_context) && (
              <div className="flex flex-wrap gap-3 mb-4">
                {analysisResult.financial_year && (
                  <span className="px-2.5 py-1 rounded-md bg-cr-50 text-primary text-xs font-mono font-semibold">
                    {analysisResult.financial_year}
                  </span>
                )}
                {analysisResult.unit_context && (
                  <span className="px-2.5 py-1 rounded-md bg-surface-2 text-ink-secondary text-xs font-mono">
                    Unit: {analysisResult.unit_context}
                  </span>
                )}
              </div>
            )}

            {analysisResult.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                {analysisResult.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-800 flex items-start gap-2">
                    <svg className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {w}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Detected Sections */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-ink-primary font-mono uppercase tracking-wide">Detected Financial Statements</h3>
            {analysisResult.sections.map((section, idx) => (
              <div key={idx} className="card p-4 border border-border-subtle hover:border-primary/30 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-cr-50 text-primary flex items-center justify-center">
                      {SECTION_ICONS[section.section_type] || SECTION_ICONS.balance_sheet}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-ink-primary">
                        {SECTION_LABELS[section.section_type] || section.section_type}
                      </div>
                      <div className="text-[11px] text-ink-secondary mt-0.5">
                        Pages {section.page_range}
                        {section.variant !== 'unknown' && (
                          <span className="ml-2 px-1.5 py-0.5 rounded bg-surface-2 text-[10px] font-mono uppercase">
                            {section.variant}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-ink-secondary">
                      <span className="font-mono font-bold text-ink-primary">{section.fields_extracted}</span> fields extracted
                    </div>
                    <div className="mt-1">{confidenceBar(section.confidence)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => {
                setAnalysisResult(null)
                setUploadedDocId(null)
              }}
              className="btn btn-secondary flex-1"
            >
              Upload Another Report
            </button>
          </div>
        </div>
      )}

      {/* Report status viewer (for previously processed reports) */}
      {reportStatus && !analysisResult && (
        <div className="card p-5 mb-6 border border-border-subtle">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-ink-primary font-mono">Report Analysis Details</h3>
              <p className="text-xs text-ink-secondary mt-0.5">{reportStatus.original_filename}</p>
            </div>
            <button onClick={() => setReportStatus(null)} className="text-xs text-ink-muted hover:text-ink-primary">
              Close
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {reportStatus.total_pages && (
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-ink-primary font-mono">{reportStatus.total_pages}</div>
                <div className="text-[10px] text-ink-muted uppercase">Pages</div>
              </div>
            )}
            <div className="bg-surface-2 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-primary font-mono">{reportStatus.sections.length}</div>
              <div className="text-[10px] text-ink-muted uppercase">Sections</div>
            </div>
            <div className="bg-surface-2 rounded-lg p-3 text-center">
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${STATUS_BADGE[reportStatus.status] ?? 'bg-gray-100 text-gray-700'}`}>
                {reportStatus.status}
              </span>
            </div>
            {reportStatus.toc_found && (
              <div className="bg-surface-2 rounded-lg p-3 text-center">
                <div className="text-xs font-bold text-green-600">TOC Detected</div>
                <div className="text-[10px] text-ink-muted uppercase">Method</div>
              </div>
            )}
          </div>

          {reportStatus.sections.length > 0 && (
            <div className="space-y-2">
              {reportStatus.sections.map(s => (
                <div key={s.id} className="flex items-center justify-between p-3 bg-surface-2 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-cr-50 text-primary flex items-center justify-center">
                      {SECTION_ICONS[s.section_type] || SECTION_ICONS.balance_sheet}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-ink-primary">{SECTION_LABELS[s.section_type] || s.section_type}</div>
                      <div className="text-[10px] text-ink-muted">Pages {s.page_range}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-ink-secondary">{s.fields_extracted} fields</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${STATUS_BADGE[s.status] ?? 'bg-gray-100 text-gray-700'}`}>
                      {s.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Previous Annual Reports */}
      {previousReports.length > 0 && !analysisResult && (
        <div>
          <h3 className="text-xs font-bold text-ink-primary font-mono uppercase tracking-wide mb-3">Previous Annual Reports</h3>
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-small">
                <thead className="bg-surface-2">
                  <tr>
                    {['Filename', 'Application', 'Year', 'Size', 'Status', 'Uploaded', 'Actions'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-surface-1 divide-y divide-border-subtle">
                  {previousReports.map(doc => (
                    <tr key={doc.id}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-primary flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
                          </svg>
                          <span className="text-xs font-medium text-ink-primary truncate max-w-[200px]">{doc.original_filename}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-secondary font-mono">{doc.application_number}</td>
                      <td className="px-4 py-3 text-xs text-ink-secondary">{doc.financial_year ?? '-'}</td>
                      <td className="px-4 py-3 text-xs text-ink-secondary tabular">{formatSize(doc.file_size_bytes)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide
                          ${STATUS_BADGE[doc.status ?? ''] ?? 'bg-gray-100 text-gray-700'}`}>
                          {doc.status ?? 'unknown'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-ink-muted">
                        {new Date(doc.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleViewStatus(doc.id)}
                          className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
