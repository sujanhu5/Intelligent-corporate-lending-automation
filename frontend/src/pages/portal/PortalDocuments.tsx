import { useEffect, useState, useRef } from 'react'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

const DOC_TYPES = [
  { value: 'balance_sheet', label: 'Balance Sheet' },
  { value: 'profit_loss', label: 'Profit & Loss Statement' },
  { value: 'cash_flow', label: 'Cash Flow Statement' },
  { value: 'annual_report', label: 'Annual Report (Auto-detect)' },
  { value: 'auditor_report', label: 'Auditor Report' },
  { value: 'gst_report', label: 'GST Report' },
  { value: 'bank_statement', label: 'Bank Statement' },
  { value: 'other', label: 'Other Document' },
]

const STATUS_BADGE: Record<string, string> = {
  uploaded: 'bg-blue-100 text-blue-800',
  processing: 'bg-amber-100 text-amber-800',
  extracted: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

interface DocItem {
  id: string
  application_id: string
  application_number: string
  document_type: string | null
  original_filename: string
  file_size_bytes: number | null
  financial_year: string | null
  status: string | null
  ocr_processed: boolean
  created_at: string
}

export default function PortalDocuments() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [docType, setDocType] = useState('balance_sheet')
  const [financialYear, setFinancialYear] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [applicationId, setApplicationId] = useState('')
  const [applications, setApplications] = useState<{ id: string; application_number: string }[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const { success, error } = useToast()

  const load = () => {
    setLoading(true)
    Promise.all([
      portalApi.documents(),
      portalApi.applications(1, 100),
    ]).then(([docData, appData]) => {
      setDocs(docData.documents)
      setApplications(appData.items.map((a: any) => ({ id: a.id, application_number: a.application_number })))
      if (appData.items.length > 0 && !applicationId) {
        setApplicationId(appData.items[0].id)
      }
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleUpload = async () => {
    if (!selectedFile || !applicationId) return
    setUploading(true)
    try {
      await portalApi.uploadDocument(applicationId, selectedFile, docType, financialYear || undefined)
      success('Document uploaded successfully.')
      setSelectedFile(null)
      setFinancialYear('')
      setShowUpload(false)
      if (fileRef.current) fileRef.current.value = ''
      load()
    } catch (err) {
      error(extractError(err))
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file)
      setShowUpload(true)
    } else {
      error('Only PDF files are accepted.')
    }
  }

  const formatSize = (bytes: number | null) => {
    if (!bytes) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (loading) return <PageLoader />

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary font-mono mb-2">Documents</div>
          <h1 className="text-h2 text-ink-primary">Financial Documents</h1>
          <p className="text-small text-ink-secondary mt-1">
            Upload and manage financial documents for your loan applications
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="btn btn-primary"
        >
          {showUpload ? 'Cancel' : 'Upload Document'}
        </button>
      </div>

      {/* Upload section */}
      {showUpload && (
        <div className="card p-6 mb-6 border-2 border-primary/20">
          <h2 className="text-sm font-bold text-ink-primary font-mono mb-4">Upload New Document</h2>

          {applications.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-sm text-ink-secondary">No applications found. Documents are uploaded against a loan application.</p>
              <p className="text-xs text-ink-muted mt-1">Contact the bank to have an application created for your company.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="label">Application</label>
                  <select
                    value={applicationId}
                    onChange={e => setApplicationId(e.target.value)}
                    className="input"
                  >
                    {applications.map(a => (
                      <option key={a.id} value={a.id}>{a.application_number}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Document Type</label>
                  <select
                    value={docType}
                    onChange={e => setDocType(e.target.value)}
                    className="input"
                  >
                    {DOC_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
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

              {/* Drop zone */}
              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-border-default rounded-xl p-8 text-center cursor-pointer
                  hover:border-primary hover:bg-cr-50 transition-colors"
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf"
                  onChange={e => {
                    const f = e.target.files?.[0]
                    if (f) setSelectedFile(f)
                  }}
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-xl bg-cr-50 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-bold text-ink-primary">{selectedFile.name}</p>
                    <p className="text-xs text-ink-muted mt-1">{formatSize(selectedFile.size)} — Click to change</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-bold text-ink-primary">
                      Drop a PDF here or click to browse
                    </p>
                    <p className="text-xs text-ink-muted mt-1">
                      Accepted: PDF files up to 20 MB
                    </p>
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                  className="btn btn-primary"
                >
                  {uploading ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Uploading...
                    </span>
                  ) : 'Upload Document'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Documents list */}
      {docs.length > 0 ? (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Filename', 'Type', 'Application', 'Year', 'Size', 'Status', 'Uploaded'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-surface-1 divide-y divide-border-subtle">
                {docs.map(doc => (
                  <tr key={doc.id}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
                        </svg>
                        <span className="text-xs font-medium text-ink-primary truncate max-w-[200px]">{doc.original_filename}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-secondary capitalize">
                      {doc.document_type?.replace(/_/g, ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-secondary font-mono">
                      {doc.application_number}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-secondary">
                      {doc.financial_year ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-secondary tabular">
                      {formatSize(doc.file_size_bytes)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide
                        ${STATUS_BADGE[doc.status ?? ''] ?? 'bg-gray-100 text-gray-700'}`}>
                        {doc.status ?? 'unknown'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-ink-muted">
                      {new Date(doc.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="w-14 h-14 rounded-xl bg-cr-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-ink-primary">No documents uploaded</h3>
          <p className="text-xs text-ink-secondary mt-1 max-w-sm mx-auto">
            Upload your financial statements, balance sheets, and other supporting documents for your loan applications.
          </p>
          <button
            onClick={() => setShowUpload(true)}
            className="btn btn-primary mt-4"
          >
            Upload Your First Document
          </button>
        </div>
      )}
    </div>
  )
}
