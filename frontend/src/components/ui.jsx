export function cx(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function Surface({ className = '', children }) {
  return (
    <div
      className={cx(
        'rounded-lg border border-gray-700/50 bg-gray-800/50 shadow-sm',
        className
      )}
    >
      {children}
    </div>
  )
}

export function SectionHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="space-y-2">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            {eyebrow}
          </p>
        )}
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold text-white">{title}</h2>
          {description && (
            <p className="max-w-2xl text-sm text-gray-400">{description}</p>
          )}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function Pill({ tone = 'default', children }) {
  const tones = {
    default: 'border-gray-600 bg-gray-700/50 text-gray-200',
    accent: 'border-gold-600/50 bg-gold-900/30 text-gold-200',
    success: 'border-green-600/50 bg-green-900/30 text-green-200',
    warning: 'border-yellow-600/50 bg-yellow-900/30 text-yellow-200',
    danger: 'border-red-600/50 bg-red-900/30 text-red-200',
  }

  return (
    <span
      className={cx(
        'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium',
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
      'bg-gold-500 text-slate-900 hover:bg-gold-600 focus:ring-2 focus:ring-gold-400 focus:ring-offset-2 focus:ring-offset-slate-900',
    secondary:
      'border-gray-600 bg-gray-700/50 text-gray-200 hover:bg-gray-700',
    ghost:
      'text-gray-300 hover:bg-gray-700/50 hover:text-white',
    danger:
      'bg-red-600 text-white hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-slate-900',
  }

  return (
    <button
      className={cx(
        'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none disabled:cursor-not-allowed disabled:opacity-50',
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
    <Surface className="p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-gray-400">{label}</p>
      <div className="mt-2 flex items-end justify-between gap-4">
        <p className="text-xl font-semibold text-white">{value}</p>
        {hint ? <p className="max-w-[12rem] text-right text-xs text-gray-500">{hint}</p> : null}
      </div>
    </Surface>
  )
}

export function Alert({ tone = 'info', title, children, className = '' }) {
  const tones = {
    info: 'border-gold-600/50 bg-gold-900/20 text-gold-100',
    success: 'border-green-600/50 bg-green-900/20 text-green-100',
    warning: 'border-yellow-600/50 bg-yellow-900/20 text-yellow-100',
    danger: 'border-red-600/50 bg-red-900/20 text-red-100',
  }

  return (
    <div className={cx('rounded-lg border p-4', tones[tone] || tones.info, className)}>
      <div className="space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <div className="text-sm text-gray-300">{children}</div>
      </div>
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <Surface className="p-8 text-center">
      <div className="mx-auto max-w-lg space-y-3">
        <p className="text-lg font-semibold text-white">{title}</p>
        <p className="text-sm text-gray-400">{description}</p>
        {action ? <div className="pt-4">{action}</div> : null}
      </div>
    </Surface>
  )
}

export function CodeBlock({ children, className = '' }) {
  return (
    <pre
      className={cx(
        'overflow-x-auto rounded-lg border border-gray-700 bg-gray-900 p-4 text-xs text-gray-200',
        className
      )}
    >
      {children}
    </pre>
  )
}
