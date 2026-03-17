/** Validation results — rich dashboard with animated metrics. */

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  Upload,
  Shield,
  ArrowRight,
  ChevronDown,
  Rows3,
  Hash,
  Target,
  Diff,
} from 'lucide-react'
import { getValidation } from '@/api'
import type { ValidationRunResponse, ValidationIssueSummary } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const SEVERITY_CONFIG = {
  error: {
    icon: AlertCircle,
    variant: 'destructive' as const,
    label: 'Errors',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    ring: 'ring-red-500/30',
    glow: 'glow-error',
  },
  warning: {
    icon: AlertTriangle,
    variant: 'outline' as const,
    label: 'Warnings',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    ring: 'ring-amber-500/30',
    glow: '',
  },
  info: {
    icon: Info,
    variant: 'secondary' as const,
    label: 'Info',
    color: 'text-sky-400',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/20',
    ring: 'ring-sky-500/30',
    glow: '',
  },
}

export default function ResultsPage() {
  const { validationId } = useParams<{ validationId: string }>()
  const [data, setData] = useState<ValidationRunResponse | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState<string | null>(null)

  useEffect(() => {
    if (!validationId) return
    getValidation(validationId)
      .then(setData)
      .catch((err) => setError(err.message))
  }, [validationId])

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="max-w-lg mx-auto py-16 text-center space-y-4"
      >
        <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto">
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>
        <p className="text-sm text-destructive">{error}</p>
        <Link to="/upload">
          <Button variant="secondary">Back to Upload</Button>
        </Link>
      </motion.div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Spinner className="h-8 w-8" />
        <p className="text-xs text-muted-foreground font-mono animate-pulse">Loading results…</p>
      </div>
    )
  }

  const { summary, issues } = data
  const filtered = filter ? issues.filter((i) => i.severity === filter) : issues
  const passRate =
    summary.rules_executed > 0
      ? Math.round((summary.passed_checks / summary.rules_executed) * 100)
      : 100
  const hasIssues = summary.errors + summary.warnings + summary.infos > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2.5">
            <Shield className="h-6 w-6 text-primary" />
            Validation Results
          </h1>
          <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-muted/50 font-mono">
              <Hash className="h-3 w-3" />
              {summary.rules_executed} rules
            </span>
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-muted/50 font-mono">
              <Rows3 className="h-3 w-3" />
              {summary.total_rows} rows
            </span>
          </div>
        </div>
        <Link to="/upload">
          <Button variant="outline" size="sm" className="gap-1.5 group">
            <Upload className="h-3.5 w-3.5" />
            New Upload
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </Link>
      </div>

      {/* Pass rate hero + metrics */}
      <div className="grid grid-cols-12 gap-4">
        {/* Pass rate ring */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className={cn(
            'col-span-12 sm:col-span-4 rounded-2xl border p-6 flex flex-col items-center justify-center gap-3',
            hasIssues
              ? 'border-border/50 bg-card'
              : 'border-emerald-500/20 bg-emerald-500/5 glow-success',
          )}
        >
          <div className="relative w-28 h-28">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                className="text-border/30"
              />
              <motion.circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                strokeWidth="6"
                strokeLinecap="round"
                className={hasIssues ? 'text-primary' : 'text-emerald-400'}
                strokeDasharray={`${2 * Math.PI * 42}`}
                initial={{ strokeDashoffset: 2 * Math.PI * 42 }}
                animate={{ strokeDashoffset: 2 * Math.PI * 42 * (1 - passRate / 100) }}
                transition={{ delay: 0.3, duration: 1, ease: 'easeOut' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-3xl font-bold text-foreground">{passRate}%</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                pass rate
              </span>
            </div>
          </div>
          <p
            className={cn(
              'text-xs font-semibold',
              hasIssues ? 'text-muted-foreground' : 'text-emerald-400',
            )}
          >
            {hasIssues
              ? `${summary.passed_checks} of ${summary.rules_executed} checks passed`
              : 'All checks passed'}
          </p>
        </motion.div>

        {/* Metric cards */}
        <div className="col-span-12 sm:col-span-8 grid grid-cols-2 gap-4">
          <MetricCard
            label="Passed"
            value={summary.passed_checks}
            icon={CheckCircle2}
            color="text-emerald-400"
            bg="bg-emerald-500/10"
            delay={0.15}
          />
          <MetricCard
            label="Errors"
            value={summary.errors}
            icon={AlertCircle}
            color="text-red-400"
            bg="bg-red-500/10"
            active={filter === 'error'}
            onClick={() => setFilter(filter === 'error' ? null : 'error')}
            delay={0.2}
          />
          <MetricCard
            label="Warnings"
            value={summary.warnings}
            icon={AlertTriangle}
            color="text-amber-400"
            bg="bg-amber-500/10"
            active={filter === 'warning'}
            onClick={() => setFilter(filter === 'warning' ? null : 'warning')}
            delay={0.25}
          />
          <MetricCard
            label="Info"
            value={summary.infos}
            icon={Info}
            color="text-sky-400"
            bg="bg-sky-500/10"
            active={filter === 'info'}
            onClick={() => setFilter(filter === 'info' ? null : 'info')}
            delay={0.3}
          />
        </div>
      </div>

      {/* Issues */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-foreground">Issues</h2>
            <Badge variant="secondary" className="font-mono text-[10px]">
              {filtered.length}
            </Badge>
            {filter && (
              <Button
                variant="ghost"
                size="xs"
                onClick={() => setFilter(null)}
                className="text-xs text-muted-foreground"
              >
                Clear filter
              </Button>
            )}
          </div>
        </div>

        {filtered.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 py-12 flex flex-col items-center gap-3"
          >
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6 text-emerald-400" />
            </div>
            <p className="text-sm font-medium text-emerald-400">
              {filter ? 'No issues at this severity level' : 'All checks passed!'}
            </p>
          </motion.div>
        ) : (
          <div className="space-y-2">
            {filtered.map((issue, i) => (
              <IssueCard key={issue.id} issue={issue} index={i} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

/* ─── Metric card ────────────────────────────────────── */

function MetricCard({
  label,
  value,
  icon: Icon,
  color,
  bg,
  onClick,
  active,
  delay = 0,
}: {
  label: string
  value: number
  icon: typeof CheckCircle2
  color: string
  bg: string
  onClick?: () => void
  active?: boolean
  delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      onClick={onClick}
      className={cn(
        'rounded-xl border p-4 transition-all duration-200',
        onClick && 'cursor-pointer hover:border-primary/30',
        active
          ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
          : 'border-border/50 bg-card',
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', bg)}>
          <Icon className={cn('h-4 w-4', color)} />
        </div>
        {onClick && (
          <ChevronDown
            className={cn(
              'h-3.5 w-3.5 text-muted-foreground/50 transition-transform',
              active && 'rotate-180 text-primary',
            )}
          />
        )}
      </div>
      <p className="font-display text-3xl font-bold text-foreground animate-count-up">{value}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
    </motion.div>
  )
}

/* ─── Issue card ─────────────────────────────────────── */

function IssueCard({ issue, index }: { issue: ValidationIssueSummary; index: number }) {
  const config = SEVERITY_CONFIG[issue.severity]
  const SevIcon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.3 }}
      className={cn(
        'group rounded-xl border p-4 transition-colors hover:bg-muted/20',
        config.border,
        'bg-card',
      )}
    >
      <div className="flex gap-3">
        {/* Severity indicator */}
        <div className={cn('w-1 self-stretch rounded-full shrink-0', config.bg)} />

        <div className="flex-1 min-w-0 space-y-2">
          {/* Top row: severity badge + rule */}
          <div className="flex items-center gap-2">
            <Badge variant={config.variant} className="gap-1">
              <SevIcon className="h-3 w-3" />
              {issue.severity}
            </Badge>
            <span className="text-[10px] font-mono text-muted-foreground/60 bg-muted/50 px-1.5 py-0.5 rounded">
              {issue.rule_id}
            </span>
          </div>

          {/* Message */}
          <p className="text-sm text-foreground font-medium leading-relaxed">{issue.message}</p>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
            {issue.row_number != null && (
              <span className="flex items-center gap-1">
                <Rows3 className="h-3 w-3 text-muted-foreground/50" />
                Row {issue.row_number}
              </span>
            )}
            {issue.field && (
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3 text-muted-foreground/50" />
                {issue.field}
              </span>
            )}
            {(issue.expected_value || issue.actual_value) && (
              <span className="flex items-center gap-1.5">
                <Diff className="h-3 w-3 text-muted-foreground/50" />
                {issue.expected_value && (
                  <span>
                    Expected:{' '}
                    <span className="text-foreground font-mono">{issue.expected_value}</span>
                  </span>
                )}
                {issue.actual_value && (
                  <span>
                    Actual:{' '}
                    <span className={cn('font-mono', config.color)}>{issue.actual_value}</span>
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
