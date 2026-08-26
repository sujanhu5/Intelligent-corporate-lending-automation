import { Link } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import ThemeToggle from '@/components/ui/ThemeToggle'

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Hero product mockup — a stylised dashboard preview
// ---------------------------------------------------------------------------

function DashboardPreview() {
  const bars = [58, 72, 64, 88, 79, 94]
  return (
    <div className="card shadow-xl p-4 sm:p-5 w-full max-w-lg relative overflow-hidden">
      {/* window chrome */}
      <div className="flex items-center gap-1.5 mb-4">
        <span className="w-2.5 h-2.5 rounded-full bg-down/70" />
        <span className="w-2.5 h-2.5 rounded-full bg-[#F4A300]/70" />
        <span className="w-2.5 h-2.5 rounded-full bg-up/70" />
        <span className="ml-3 text-[10px] text-ink-muted font-mono">cla / credit-assessment</span>
      </div>

      {/* stat tiles */}
      <div className="grid grid-cols-3 gap-2.5 mb-4">
        {[
          { l: 'Risk Score', v: '16.0', d: '↓ low', up: true },
          { l: 'PD', v: '4.2%', d: '↓ 1.1', up: true },
          { l: 'Decision', v: 'PASS', d: 'auto', up: true },
        ].map(s => (
          <div key={s.l} className="rounded-lg bg-surface-2 border border-border-subtle p-2.5">
            <div className="text-[8px] font-bold uppercase tracking-wider text-ink-muted font-mono">{s.l}</div>
            <div className="text-lg font-extrabold text-ink-primary font-mono tabular leading-none mt-1">{s.v}</div>
            <div className="text-[9px] font-bold text-up font-mono mt-1">{s.d}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* mini donut */}
        <div className="rounded-lg bg-surface-2 border border-border-subtle p-3">
          <div className="text-[9px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-2">Status Mix</div>
          <div className="flex items-center justify-center py-1">
            <svg viewBox="0 0 42 42" className="w-24 h-24">
              <circle cx="21" cy="21" r="15.9" fill="none" stroke="var(--surface-1)" strokeWidth="6" />
              <circle cx="21" cy="21" r="15.9" fill="none" stroke="#12A150" strokeWidth="6"
                strokeDasharray="45 55" strokeDashoffset="25" />
              <circle cx="21" cy="21" r="15.9" fill="none" stroke="var(--cr-500)" strokeWidth="6"
                strokeDasharray="30 70" strokeDashoffset="-20" />
              <circle cx="21" cy="21" r="15.9" fill="none" stroke="#E5484D" strokeWidth="6"
                strokeDasharray="15 85" strokeDashoffset="-50" />
              <text x="21" y="23" textAnchor="middle" className="fill-ink-primary" style={{ fontSize: 7, fontWeight: 800, fontFamily: 'JetBrains Mono' }}>6</text>
            </svg>
          </div>
        </div>

        {/* mini bars */}
        <div className="rounded-lg bg-surface-2 border border-border-subtle p-3">
          <div className="text-[9px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-2">Model ROC-AUC</div>
          <div className="flex items-end justify-between gap-1.5 h-[86px] pt-2">
            {bars.map((h, i) => (
              <div key={i} className="flex-1 rounded-t gradient-orange" style={{ height: `${h}%`, opacity: 0.55 + i * 0.075 }} />
            ))}
          </div>
        </div>
      </div>

      {/* pipeline mini strip */}
      <div className="flex items-center gap-1 mt-4">
        {['OCR', 'Ratios', 'Rules', 'ML', 'Report'].map((s, i) => (
          <div key={s} className="flex items-center flex-1 last:flex-none">
            <div className={`h-6 flex-1 rounded-md flex items-center justify-center text-[8px] font-bold font-mono uppercase
              ${i < 4 ? 'gradient-orange text-white' : 'bg-surface-2 border border-border-subtle text-ink-muted'}`}>
              {s}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Feature card
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const FEATURES = [
  { icon: '⌫', title: 'Document OCR', body: 'Pull figures straight from balance sheets, P&L, and cash-flow PDFs — no manual data entry, no re-keying.' },
  { icon: '％', title: 'Financial Ratios', body: '20+ liquidity, leverage, coverage and profitability ratios computed and benchmarked against banking thresholds.' },
  { icon: '⚙', title: 'Rule Engine', body: 'Encode your credit policy as mandatory and advisory rules. Auto-reject on hard breaches, flag the rest for review.' },
  { icon: '◈', title: 'ML Risk Scoring', body: 'Logistic Regression, Random Forest and XGBoost predict default probability — every score explained with SHAP.' },
  { icon: '▤', title: 'Credit Reports', body: 'Six-page PDF credit reports generated on demand — ratios, rules, risk and recommendation, ready for committee.' },
  { icon: '⟐', title: 'Pipeline Orchestration', body: 'Run the full assessment from intake to decision in one click, or batch-process the entire backlog automatically.' },
]

const STATS = [
  { v: '0.95', l: 'Best ROC-AUC' },
  { v: '6,819', l: 'Companies Trained' },
  { v: '6-Stage', l: 'Automated Pipeline' },
  { v: '11', l: 'Credit Rules' },
]

const STAGES = ['Submit', 'OCR', 'Ratios', 'Rules', 'ML', 'Report', 'Decision']

export default function Landing() {
  const { user } = useAuthStore()
  const cta = user
    ? { to: '/dashboard', label: 'Go to Dashboard →' }
    : { to: '/login', label: 'Sign in →' }

  return (
    <div className="min-h-screen bg-canvas text-ink-primary">
      {/* ---- Nav ---- */}
      <header className="sticky top-0 z-30 bg-canvas/80 backdrop-blur-md border-b border-border-subtle">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo />
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold font-mono text-ink-secondary">
            <a href="#platform" className="hover:text-primary transition-colors">Platform</a>
            <a href="#pipeline" className="hover:text-primary transition-colors">Pipeline</a>
            <a href="#intelligence" className="hover:text-primary transition-colors">Intelligence</a>
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle variant="switch" />
            <Link to={cta.to} className="btn btn-primary btn-sm">{cta.label}</Link>
          </div>
        </div>
      </header>

      {/* ---- Hero ---- */}
      <section className="relative overflow-hidden grid-bg">
        <div className="max-w-6xl mx-auto px-6 pt-16 pb-20 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <Eyebrow>AI-Powered Credit Engine</Eyebrow>
            <h1 className="mt-6 font-mono font-extrabold text-ink-primary text-[2.6rem] sm:text-[3.25rem] leading-[1.03] tracking-tight text-balance">
              Financial statements<br />into <span className="text-primary">credit decisions.</span>
            </h1>
            <p className="mt-6 text-ink-secondary text-base leading-relaxed max-w-lg">
              CLA is an end-to-end corporate lending automation platform. It reads financial documents,
              computes the ratios, applies your credit policy, and scores default risk with explainable
              machine learning — turning a week of manual underwriting into minutes.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to={cta.to} className="btn btn-primary btn-lg">{cta.label}</Link>
              <a href="#pipeline" className="btn btn-secondary btn-lg">See the pipeline</a>
            </div>
            <div className="mt-8 flex items-center gap-2 text-[11px] text-ink-muted font-mono uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-up" />
              Trained on the Taiwanese corporate bankruptcy dataset
            </div>
          </div>

          <div className="flex justify-center lg:justify-end">
            <DashboardPreview />
          </div>
        </div>
      </section>

      {/* ---- Stats band ---- */}
      <section className="border-y border-border-subtle bg-surface-1">
        <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-2 lg:grid-cols-4 gap-6">
          {STATS.map(s => (
            <div key={s.l} className="text-center">
              <div className="text-3xl font-extrabold text-ink-primary font-mono tabular">{s.v}</div>
              <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-muted font-mono mt-1.5">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ---- Features ---- */}
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

      {/* ---- Pipeline flow ---- */}
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

      {/* ---- Intelligence band ---- */}
      <section id="intelligence" className="max-w-6xl mx-auto px-6 py-20">
        <div className="card p-8 sm:p-12 grid lg:grid-cols-2 gap-10 items-center relative overflow-hidden">
          <div className="absolute -right-16 -top-16 w-56 h-56 rounded-full bg-cr-50 opacity-70" />
          <div className="relative">
            <Eyebrow>Explainable ML</Eyebrow>
            <h2 className="mt-5 font-mono font-extrabold text-ink-primary text-[1.75rem] leading-tight tracking-tight">
              Not a black box.
            </h2>
            <p className="mt-4 text-ink-secondary leading-relaxed">
              Three models compete on every retrain — Logistic Regression, Random Forest and XGBoost —
              and the strongest is selected by ROC-AUC. Every prediction ships with SHAP feature
              attributions, so an officer can see exactly which financial signals drove the score.
            </p>
            <ul className="mt-6 flex flex-col gap-2.5">
              {[
                'SMOTE-balanced training on 6,819 companies',
                'Mutual-information feature selection (top 30)',
                'Composite 0–100 risk score with clear risk bands',
              ].map(item => (
                <li key={item} className="flex items-center gap-2.5 text-small text-ink-primary">
                  <span className="w-5 h-5 rounded-full gradient-orange text-white flex items-center justify-center text-[10px] flex-shrink-0">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative flex justify-center">
            <div className="grid grid-cols-2 gap-3 w-full max-w-xs">
              {[
                { m: 'Random Forest', v: '0.949', best: true },
                { m: 'XGBoost', v: '0.937', best: false },
                { m: 'Logistic Reg.', v: '0.934', best: false },
                { m: 'CV Mean', v: '0.996', best: false },
              ].map(x => (
                <div key={x.m} className={`rounded-xl p-4 border ${x.best ? 'gradient-orange border-transparent text-white shadow-orange' : 'bg-surface-2 border-border-subtle'}`}>
                  <div className={`text-2xl font-extrabold font-mono tabular ${x.best ? 'text-white' : 'text-ink-primary'}`}>{x.v}</div>
                  <div className={`text-[9px] font-bold uppercase tracking-wider font-mono mt-1 ${x.best ? 'text-white/80' : 'text-ink-muted'}`}>{x.m}{x.best && ' ★'}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---- CTA ---- */}
      <section className="bg-surface-1 border-t border-border-subtle">
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <h2 className="font-mono font-extrabold text-ink-primary text-[2rem] leading-tight tracking-tight text-balance">
            Ready to automate your credit desk?
          </h2>
          <p className="mt-4 text-ink-secondary max-w-lg mx-auto">
            Sign in to the platform and run a full corporate loan assessment end to end.
          </p>
          <div className="mt-8">
            <Link to={cta.to} className="btn btn-primary btn-lg">{cta.label}</Link>
          </div>
        </div>
      </section>

      {/* ---- Footer ---- */}
      <footer className="border-t border-border-subtle">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Logo />
          <div className="text-[11px] text-ink-muted font-mono uppercase tracking-wider text-center">
            Corporate Lending Automation · Final Year Engineering Project · 2026
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono text-ink-secondary">
            <a href="#platform" className="hover:text-primary transition-colors">Platform</a>
            <Link to={cta.to} className="hover:text-primary transition-colors">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
