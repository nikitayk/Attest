export function cx(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function Surface({ className = '', children }) {
  return (
    <div
      className={cx(
        'rounded-3xl border border-white/10 bg-white/[0.05] shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl',
        className
      )}
    >
      {children}
    </div>
  )
}

export function SectionHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-3">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300/80">
            {eyebrow}
          </p>
        )}
        <div className="space-y-2">
          <h2 className="text-3xl font-semibold tracking-tight text-white">{title}</h2>
          {description && (
            <p className="max-w-2xl text-sm leading-6 text-slate-300">{description}</p>
          )}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  )
}

export function Pill({ tone = 'default', children }) {
  const tones = {
    default: 'border-white/10 bg-white/[0.08] text-slate-200',
    accent: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-200',
    success: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200',
    warning: 'border-amber-400/20 bg-amber-400/10 text-amber-200',
    danger: 'border-rose-400/20 bg-rose-400/10 text-rose-200',
  }

  return (
    <span
      className={cx(
        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium tracking-wide',
        tones[tone] || tones.default
      )}
    >
      {children}
    </span>
  )
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  disabled = false,
  ...props
}) {
  const variants = {
    primary:
      'border-cyan-400/30 bg-cyan-400/90 text-slate-950 hover:bg-cyan-300',
    secondary:
      'border-white/10 bg-white/[0.08] text-white hover:bg-white/[0.12]',
    ghost:
      'border-transparent bg-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.06] hover:text-white',
    danger:
      'border-rose-400/20 bg-rose-400/10 text-rose-100 hover:bg-rose-400/20',
  }

  return (
    <button
      className={cx(
        'inline-flex items-center justify-center rounded-2xl border px-4 py-2.5 text-sm font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-300/50 disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant] || variants.primary,
        className
      )}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}

export function MetricCard({ label, value, hint }) {
  return (
    <Surface className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <div className="mt-4 flex items-end justify-between gap-4">
        <p className="text-3xl font-semibold text-white">{value}</p>
        {hint ? <p className="max-w-[12rem] text-right text-xs text-slate-400">{hint}</p> : null}
      </div>
    </Surface>
  )
}

export function Alert({ tone = 'info', title, children, className = '' }) {
  const tones = {
    info: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-100',
    success: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-100',
    warning: 'border-amber-400/20 bg-amber-400/10 text-amber-100',
    danger: 'border-rose-400/20 bg-rose-400/10 text-rose-100',
  }

  return (
    <div className={cx('rounded-2xl border p-4', tones[tone] || tones.info, className)}>
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <div className="text-sm leading-6 opacity-90">{children}</div>
      </div>
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <Surface className="p-8 text-center">
      <div className="mx-auto max-w-lg space-y-3">
        <p className="text-xl font-semibold text-white">{title}</p>
        <p className="text-sm leading-6 text-slate-300">{description}</p>
        {action ? <div className="pt-2">{action}</div> : null}
      </div>
    </Surface>
  )
}

export function CodeBlock({ children, className = '' }) {
  return (
    <pre
      className={cx(
        'overflow-x-auto rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-xs leading-6 text-slate-200',
        className
      )}
    >
      {children}
    </pre>
  )
}
