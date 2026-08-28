import { Link } from 'react-router-dom'
import ThemeToggle from '@/components/ui/ThemeToggle'

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-9 h-9 rounded-lg gradient-orange flex items-center justify-center shadow-orange">
        <span className="text-white font-extrabold text-sm font-mono tracking-tighter">CL</span>
      </div>
      <div className="leading-none">
        <div className="text-sm font-extrabold text-ink-primary font-mono">CLA</div>
        <div className="text-[9px] text-ink-muted uppercase tracking-[0.14em] font-mono mt-0.5">Lending OS</div>
      </div>
    </div>
  )
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-primary font-mono
                    bg-cr-50 px-3 py-1.5 rounded-full border border-cr-200/60">
      <span className="w-1.5 h-1.5 rounded-full bg-primary" />
      {children}
    </div>
  )
}

function Feature({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="card card-hover p-6">
      <div className="w-11 h-11 rounded-xl gradient-orange flex items-center justify-center text-lg text-white shadow-orange mb-4">
        {icon}
      </div>
      <h3 className="text-base font-bold text-ink-primary mb-1.5 font-mono">{title}</h3>
      <p className="text-small text-ink-secondary leading-relaxed">{body}</p>
    </div>
  )
}

const FEATURES = [
  { icon: '⌫', title: 'Document OCR', body: 'Upload balance sheets, P&L statements, and cash-flow PDFs. Our OCR engine extracts financial data automatically.' },
  { icon: '％', title: 'Financial Ratios', body: 'Liquidity, leverage, coverage, and profitability ratios computed and benchmarked against industry standards.' },
  { icon: '⚙', title: 'Rule Engine', body: 'Credit policy encoded as configurable rules. Auto-reject on hard breaches, flag edge cases for manual review.' },
  { icon: '◈', title: 'ML Risk Scoring', body: 'Machine learning models predict default probability with SHAP-based explanations for every score.' },
  { icon: '▤', title: 'Credit Reports', body: 'Comprehensive PDF credit reports generated on demand — ratios, rules, risk assessment, and recommendations.' },
  { icon: '⟐', title: 'Pipeline Orchestration', body: 'Run the full assessment from document intake to credit decision in a single automated pipeline.' },
]

const STAGES = ['Submit', 'OCR', 'Ratios', 'Rules', 'ML', 'Report', 'Decision']

export default function Landing() {
  return (
    <div className="min-h-screen bg-canvas text-ink-primary">
      {/* Nav */}
      <header className="sticky top-0 z-30 bg-canvas/80 backdrop-blur-md border-b border-border-subtle">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo />
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold font-mono text-ink-secondary">
            <a href="#platform" className="hover:text-primary transition-colors">Platform</a>
            <a href="#pipeline" className="hover:text-primary transition-colors">Pipeline</a>
            <a href="#how-it-works" className="hover:text-primary transition-colors">How It Works</a>
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle variant="switch" />
            <Link to="/login" className="btn btn-secondary btn-sm">Sign In</Link>
            <Link to="/register" className="btn btn-primary btn-sm">Apply for Loan</Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden grid-bg">
        <div className="max-w-6xl mx-auto px-6 pt-20 pb-24 text-center">
          <Eyebrow>Corporate Credit Assessment Platform</Eyebrow>
          <h1 className="mt-6 font-mono font-extrabold text-ink-primary text-[2.6rem] sm:text-[3.25rem] leading-[1.03] tracking-tight text-balance max-w-3xl mx-auto">
            Financial documents<br />into <span className="text-primary">credit decisions.</span>
          </h1>
          <p className="mt-6 text-ink-secondary text-base leading-relaxed max-w-xl mx-auto">
            CLA automates corporate loan underwriting — from document intake to risk scoring
            to final credit decision. Upload your financial statements and get an assessment.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/register" className="btn btn-primary btn-lg">Apply for a Loan</Link>
            <Link to="/login" className="btn btn-secondary btn-lg">Sign In</Link>
            <a href="#pipeline" className="btn btn-secondary btn-lg">See the Pipeline</a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="platform" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <Eyebrow>The Platform</Eyebrow>
          <h2 className="mt-5 font-mono font-extrabold text-ink-primary text-[2rem] leading-tight tracking-tight text-balance">
            Every step of underwriting, automated.
          </h2>
          <p className="mt-4 text-ink-secondary max-w-xl mx-auto">
            Six specialised engines chain together so a loan officer can go from a stack of PDFs
            to a defensible credit decision without leaving the screen.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map(f => <Feature key={f.title} {...f} />)}
        </div>
      </section>

      {/* Pipeline flow */}
      <section id="pipeline" className="bg-surface-1 border-y border-border-subtle">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center mb-14">
            <Eyebrow>The Pipeline</Eyebrow>
            <h2 className="mt-5 font-mono font-extrabold text-ink-primary text-[2rem] leading-tight tracking-tight">
              Intake to decision, in one flow.
            </h2>
          </div>
          <div className="flex items-center justify-center flex-wrap gap-y-6">
            {STAGES.map((stage, i) => (
              <div key={stage} className="flex items-center">
                <div className="flex flex-col items-center gap-2 w-[92px]">
                  <div className={`w-11 h-11 rounded-full flex items-center justify-center text-xs font-extrabold font-mono border-2
                    ${i < STAGES.length - 1 ? 'gradient-orange text-white border-transparent shadow-orange' : 'bg-surface-2 border-primary text-primary'}`}>
                    {i + 1}
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wide font-mono text-ink-secondary">{stage}</span>
                </div>
                {i < STAGES.length - 1 && (
                  <div className="w-6 sm:w-10 h-0.5 -mt-6 rounded-full gradient-orange" />
                )}
              </div>
            ))}
          </div>
          <p className="text-center text-small text-ink-secondary max-w-xl mx-auto mt-12">
            A mandatory rule breach rejects the application before ML ever runs. Everything else flows
            through to an explainable risk score and a generated credit report.
          </p>
        </div>
      </section>

      {/* How it works — for companies */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <Eyebrow>For Companies</Eyebrow>
          <h2 className="mt-5 font-mono font-extrabold text-ink-primary text-[2rem] leading-tight tracking-tight text-balance">
            Apply for a corporate loan in minutes.
          </h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { step: '1', title: 'Register Your Company', body: 'Create an account with your company details and documents. Registration takes less than 5 minutes.' },
            { step: '2', title: 'Upload Financial Statements', body: 'Upload balance sheets, P&L, and cash-flow documents. Our OCR extracts the data automatically.' },
            { step: '3', title: 'Track Your Application', body: 'Monitor your application in real-time through every stage — from document processing to final decision.' },
          ].map(item => (
            <div key={item.step} className="card p-6 text-center">
              <div className="w-12 h-12 rounded-full gradient-orange text-white flex items-center justify-center text-lg font-extrabold font-mono mx-auto mb-4 shadow-orange">
                {item.step}
              </div>
              <h3 className="text-base font-bold text-ink-primary mb-2 font-mono">{item.title}</h3>
              <p className="text-small text-ink-secondary">{item.body}</p>
            </div>
          ))}
        </div>
        <div className="text-center mt-8">
          <Link to="/register" className="btn btn-primary btn-lg">Register Your Company</Link>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-surface-1 border-t border-border-subtle">
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <h2 className="font-mono font-extrabold text-ink-primary text-[2rem] leading-tight tracking-tight text-balance">
            Ready to get started?
          </h2>
          <p className="mt-4 text-ink-secondary max-w-lg mx-auto">
            Register your company and apply for a corporate loan, or sign in if you already have an account.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/register" className="btn btn-primary btn-lg">Apply for a Loan</Link>
            <Link to="/login" className="btn btn-secondary btn-lg">Sign In</Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-subtle">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Logo />
          <div className="text-[11px] text-ink-muted font-mono uppercase tracking-wider text-center">
            Corporate Lending Automation
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono text-ink-secondary">
            <a href="#platform" className="hover:text-primary transition-colors">Platform</a>
            <Link to="/login" className="hover:text-primary transition-colors">Sign in</Link>
            <Link to="/register" className="hover:text-primary transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
