/** Validation results — rich dashboard with animated metrics. */

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  Upload,
  Shield,
  ArrowRight,
  ChevronRight,
  Rows3,
  Hash,
  Target,
  Diff,
  CircleCheck,
} from 'lucide-react'
import { getValidation } from '@/api'
import type { ValidationRunResponse, ValidationIssueSummary } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

/** Convert snake_case rule IDs to readable Title Case */
function formatRuleId(id: string) {
  return id
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/* ─── All known rules ────────────────────────────────── */

const ALL_RULES: { rule_id: string; description: string }[] = [
  {
    rule_id: 'missing_titles',
    description: 'Every row must have a product identifier (ISBN, Artnr, or Titel)',
  },
  {
    rule_id: 'invalid_rates',
    description: 'Royalty rate must be present, non-negative, and within reasonable bounds',
  },
  {
    rule_id: 'amount_consistency',
    description: 'Quantity × Unit Price × Rate must equal the reported royalty amount',
  },
  {
    rule_id: 'tax_validation',
    description: 'Tax/duty (Afgift) lines must be present and structurally valid',
  },
  {
    rule_id: 'guarantee_validation',
    description: 'Guarantee deductions must be valid and balance within the file',
  },
  {
    rule_id: 'settlement_totals',
    description: 'Settlement totals must balance: sales subtotal → deductions → payout',
  },
  {
    rule_id: 'duplicate_entries',
    description: 'No two rows should share the same key dimensions unless intentional',
  },
  {
    rule_id: 'date_validation',
    description: 'Dates must be within valid settlement period ranges',
  },
  {
    rule_id: 'advance_balance',
    description: 'Advance offsets must not exceed the original advance amount',
  },
  {
    rule_id: 'recipient_shares',
    description: 'Co-author/recipient percentage shares must sum to ≤ 100%',
  },
  {
    rule_id: 'transaction_types',
    description: 'Transaction type must be a recognized Schilling type',
  },
]

/* ─── Severity config ────────────────────────────────── */

const SEVERITY_CONFIG = {
  error: {
    icon: AlertCircle,
    variant: 'destructive' as const,
    label: 'Errors',
    subtitle: 'Rules that found critical issues requiring correction',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    badgeBg: 'bg-red-500/10 text-red-400 border-red-500/20',
  },
  warning: {
    icon: AlertTriangle,
    variant: 'outline' as const,
    label: 'Warnings',
    subtitle: 'Potential issues that should be reviewed but may not be critical',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    badgeBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  },
  info: {
    icon: Info,
    variant: 'secondary' as const,
    label: 'Info',
    subtitle: 'Informational observations — no action required',
    color: 'text-sky-400',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/20',
    badgeBg: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  },
}

type SeverityKey = keyof typeof SEVERITY_CONFIG

export default function ResultsPage() {
  const { validationId } = useParams<{ validationId: string }>()
  const [data, setData] = useState<ValidationRunResponse | null>(null)
  const [error, setError] = useState('')
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    error: true,
    warning: false,
    info: false,
    passed: false,
  })

  const toggleSection = (key: string) => setOpenSections((s) => ({ ...s, [key]: !s[key] }))

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
  const passRate =
    summary.rules_executed > 0
      ? Math.round((summary.passed_checks / summary.rules_executed) * 100)
      : 100
  const hasIssues = summary.errors + summary.warnings + summary.infos > 0

  // Group issues by severity
  const errorIssues = issues.filter((i) => i.severity === 'error')
  const warningIssues = issues.filter((i) => i.severity === 'warning')
  const infoIssues = issues.filter((i) => i.severity === 'info')

  // Derive passed rules: all known rules minus those that produced errors
  const errorRuleIds = new Set(errorIssues.map((i) => i.rule_id))
  const passedRules = ALL_RULES.filter((r) => !errorRuleIds.has(r.rule_id))

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
          <p className="text-sm text-muted-foreground mt-1 max-w-md">
            Your file was checked against {summary.rules_executed} validation rules across{' '}
            {summary.total_rows} rows.
          </p>
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

      {/* Pass rate hero + metric cards */}
      <div className="grid grid-cols-12 gap-4">
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

        <div className="col-span-12 sm:col-span-8 grid grid-cols-4 gap-3">
          <MetricCard
            label="Passed"
            value={summary.passed_checks}
            subtitle="Rules with no errors"
            icon={CheckCircle2}
            color="text-emerald-400"
            bg="bg-emerald-500/10"
            onClick={() => toggleSection('passed')}
            active={openSections.passed}
            delay={0.15}
          />
          <MetricCard
            label="Errors"
            value={summary.errors}
            subtitle="Critical issues found"
            icon={AlertCircle}
            color="text-red-400"
            bg="bg-red-500/10"
            onClick={() => toggleSection('error')}
            active={openSections.error}
            delay={0.2}
          />
          <MetricCard
            label="Warnings"
            value={summary.warnings}
            subtitle="Possible problems"
            icon={AlertTriangle}
            color="text-amber-400"
            bg="bg-amber-500/10"
            onClick={() => toggleSection('warning')}
            active={openSections.warning}
            delay={0.25}
          />
          <MetricCard
            label="Info"
            value={summary.infos}
            subtitle="Observations"
            icon={Info}
            color="text-sky-400"
            bg="bg-sky-500/10"
            onClick={() => toggleSection('info')}
            active={openSections.info}
            delay={0.3}
          />
        </div>
      </div>

      {/* ── Collapsible sections ─────────────────────── */}

      {/* Errors */}
      {errorIssues.length > 0 && (
        <IssueSection
          severity="error"
          issues={errorIssues}
          open={openSections.error}
          onToggle={() => toggleSection('error')}
        />
      )}

      {/* Warnings */}
      {warningIssues.length > 0 && (
        <IssueSection
          severity="warning"
          issues={warningIssues}
          open={openSections.warning}
          onToggle={() => toggleSection('warning')}
        />
      )}

      {/* Info */}
      {infoIssues.length > 0 && (
        <IssueSection
          severity="info"
          issues={infoIssues}
          open={openSections.info}
          onToggle={() => toggleSection('info')}
        />
      )}

      {/* Passed Rules */}
      <div>
        <button
          onClick={() => toggleSection('passed')}
          className="flex items-center gap-2 mb-3 cursor-pointer w-full text-left"
        >
          <ChevronRight
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-200',
              openSections.passed && 'rotate-90',
            )}
          />
          <CircleCheck className="h-4 w-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-foreground">Passed Rules</h2>
          <Badge
            variant="secondary"
            className="font-mono text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          >
            {passedRules.length}
          </Badge>
          <span className="text-xs text-muted-foreground ml-1 hidden sm:inline">
            — Rules that found no critical issues
          </span>
        </button>

        <AnimatePresence>
          {openSections.passed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="space-y-1.5">
                {passedRules.map((rule, i) => (
                  <motion.div
                    key={rule.rule_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.2 }}
                    className="flex items-start gap-3 px-4 py-3 rounded-lg border border-emerald-500/10 bg-emerald-500/[0.03]"
                  >
                    <CircleCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground font-medium">{rule.description}</p>
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                        {formatRuleId(rule.rule_id)}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* No issues at all */}
      {!hasIssues && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 py-10 flex flex-col items-center gap-3"
        >
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <CheckCircle2 className="h-6 w-6 text-emerald-400" />
          </div>
          <p className="text-sm font-semibold text-emerald-400">All checks passed!</p>
          <p className="text-xs text-muted-foreground max-w-xs text-center">
            No errors, warnings, or informational notices were found. Your file is clean.
          </p>
        </motion.div>
      )}
    </motion.div>
  )
}

/* ─── Collapsible issue section ──────────────────────── */

function IssueSection({
  severity,
  issues,
  open,
  onToggle,
}: {
  severity: SeverityKey
  issues: ValidationIssueSummary[]
  open: boolean
  onToggle: () => void
}) {
  const config = SEVERITY_CONFIG[severity]
  const SevIcon = config.icon

  // Group by rule_id for context
  const ruleGroups = new Map<string, { description: string; issues: ValidationIssueSummary[] }>()
  for (const issue of issues) {
    const existing = ruleGroups.get(issue.rule_id)
    if (existing) {
      existing.issues.push(issue)
    } else {
      ruleGroups.set(issue.rule_id, { description: issue.rule_description, issues: [issue] })
    }
  }

  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-2 mb-3 cursor-pointer w-full text-left"
      >
        <ChevronRight
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform duration-200',
            open && 'rotate-90',
          )}
        />
        <SevIcon className={cn('h-4 w-4', config.color)} />
        <h2 className="text-sm font-semibold text-foreground">{config.label}</h2>
        <Badge variant="secondary" className={cn('font-mono text-[10px]', config.badgeBg)}>
          {issues.length}
        </Badge>
        <span className="text-xs text-muted-foreground ml-1 hidden sm:inline">
          — {config.subtitle}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="space-y-4">
              {[...ruleGroups.entries()].map(([ruleId, group], gi) => (
                <motion.div
                  key={ruleId}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: gi * 0.05, duration: 0.25 }}
                >
                  {/* Rule header */}
                  <div className={cn('flex items-start gap-2 mb-2 px-1')}>
                    <SevIcon className={cn('h-3.5 w-3.5 mt-0.5 shrink-0', config.color)} />
                    <div>
                      <p className="text-xs font-semibold text-foreground">{group.description}</p>
                      <p className="text-[10px] text-muted-foreground/50">
                        {formatRuleId(ruleId)} · {group.issues.length} occurrence
                        {group.issues.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  {/* Individual issues */}
                  <div className="space-y-1.5">
                    {group.issues.map((issue, i) => (
                      <IssueCard key={issue.id} issue={issue} index={i} severity={severity} />
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ─── Metric card ────────────────────────────────────── */

function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
  color,
  bg,
  onClick,
  active,
  delay = 0,
}: {
  label: string
  value: number
  subtitle: string
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
        'rounded-xl border p-3 transition-all duration-200',
        onClick && 'cursor-pointer hover:border-primary/30',
        active
          ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
          : 'border-border/50 bg-card',
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center', bg)}>
          <Icon className={cn('h-3.5 w-3.5', color)} />
        </div>
        {onClick && (
          <ChevronRight
            className={cn(
              'h-3 w-3 text-muted-foreground/50 transition-transform',
              active && 'rotate-90 text-primary',
            )}
          />
        )}
      </div>
      <p className="font-display text-2xl font-bold text-foreground leading-none">{value}</p>
      <p className="text-[11px] text-muted-foreground mt-1">{label}</p>
      <p className="text-[10px] text-muted-foreground/50 mt-0.5 leading-tight">{subtitle}</p>
    </motion.div>
  )
}

/* ─── Issue card ─────────────────────────────────────── */

function IssueCard({
  issue,
  index,
  severity,
}: {
  issue: ValidationIssueSummary
  index: number
  severity: SeverityKey
}) {
  const config = SEVERITY_CONFIG[severity]

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.02, 0.2), duration: 0.2 }}
      className={cn(
        'rounded-lg border px-4 py-3 transition-colors hover:bg-muted/20',
        config.border,
        'bg-card',
      )}
    >
      <div className="flex gap-3">
        <div className={cn('w-1 self-stretch rounded-full shrink-0', config.bg)} />
        <div className="flex-1 min-w-0 space-y-1.5">
          <p className="text-sm text-foreground leading-relaxed">{issue.message}</p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
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
            {issue.expected_value && (
              <span className="flex items-center gap-1">
                <Diff className="h-3 w-3 text-muted-foreground/50" />
                Expected: <span className="text-foreground font-mono">{issue.expected_value}</span>
              </span>
            )}
            {issue.actual_value && (
              <span>
                Actual: <span className={cn('font-mono', config.color)}>{issue.actual_value}</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
