/** Validation results — rich dashboard with animated metrics. */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  Upload,
  Shield,
  ChevronRight,
  ChevronUp,
  Rows3,
  Hash,
  Target,
  Diff,
  CircleCheck,
  FileDown,
  FileSearch,
  PanelRightOpen,
  PanelRightClose,
  FileText,
  MessageSquare,
  MoreHorizontal,
} from 'lucide-react'
import { getValidation, downloadValidationPdf, downloadAnnotatedPdf } from '@/api'
import type { ValidationRunResponse, ValidationIssueSummary } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import DocumentPreview from '@/components/DocumentPreview'
import DocumentChat from '@/components/DocumentChat'

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
  const [downloading, setDownloading] = useState(false)
  const [downloadingAnnotated, setDownloadingAnnotated] = useState(false)
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    error: true,
    warning: false,
    info: false,
    passed: false,
  })
  // Right panel state
  const [panelOpen, setPanelOpen] = useState(true)
  const [panelTab, setPanelTab] = useState<'preview' | 'chat'>('preview')
  const [docContent, setDocContent] = useState('')
  const [docFilename, setDocFilename] = useState('')
  const [showScrollTop, setShowScrollTop] = useState(false)
  const leftPanelRef = useRef<HTMLDivElement>(null)
  const hasAnimated = useRef(false)

  const handleContentLoaded = useCallback((content: string, filename: string) => {
    setDocContent(content)
    setDocFilename(filename)
  }, [])

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
    <div className="flex flex-col lg:flex-row gap-0 flex-1 min-h-0">
      {/* Mobile panel toggle bar — shows when panel is available but stacked */}
      <div className="flex lg:hidden items-center gap-1 border-b border-border/50 -mx-4 sm:-mx-6 px-4 shrink-0">
        <button
          onClick={() => {
            setPanelOpen(false)
            setPanelTab('preview')
          }}
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2',
            !panelOpen
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          <Shield className="h-3.5 w-3.5" />
          Results
        </button>
        <button
          onClick={() => {
            setPanelOpen(true)
            setPanelTab('preview')
          }}
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2',
            panelOpen && panelTab === 'preview'
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          <FileText className="h-3.5 w-3.5" />
          Preview
        </button>
        <button
          onClick={() => {
            setPanelOpen(true)
            setPanelTab('chat')
          }}
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2',
            panelOpen && panelTab === 'chat'
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          AI Chat
        </button>
      </div>

      {/* ── Left: Validation Results ── */}
      <motion.div
        ref={leftPanelRef}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        onScroll={(e) => {
          const target = e.currentTarget
          setShowScrollTop(target.scrollTop > 300)
        }}
        className={cn(
          'relative space-y-4 lg:space-y-6 pb-4 overflow-y-auto lg:pr-4 transition-all duration-300 scrollbar-gutter-stable',
          // On mobile: full width, hidden when panel is open
          panelOpen ? 'hidden lg:block' : 'flex-1',
          // On desktop: 40% or full width
          panelOpen ? 'lg:w-[40%] lg:shrink-0 lg:min-w-0' : 'lg:flex-1',
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 sticky top-0 z-10 bg-background pb-3 -mb-3">
          <div className="min-w-0">
            <h1 className="font-display text-xl sm:text-2xl font-bold text-foreground flex items-center gap-2">
              <Shield className="h-5 w-5 sm:h-6 sm:w-6 text-primary shrink-0" />
              Validation Results
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-md">
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                disabled={downloading || downloadingAnnotated}
              >
                {downloading || downloadingAnnotated ? (
                  <Spinner className="h-3.5 w-3.5" />
                ) : (
                  <MoreHorizontal className="h-3.5 w-3.5" />
                )}
                {downloading ? 'Generating…' : downloadingAnnotated ? 'Generating…' : 'Actions'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={async () => {
                  if (!validationId) return
                  setDownloading(true)
                  try {
                    await downloadValidationPdf(validationId)
                  } catch {
                    // silently fail — user can retry
                  } finally {
                    setDownloading(false)
                  }
                }}
              >
                <FileDown className="h-4 w-4" />
                Export Validation PDF
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={async () => {
                  if (!validationId) return
                  setDownloadingAnnotated(true)
                  try {
                    await downloadAnnotatedPdf(validationId)
                  } catch {
                    // silently fail — user can retry
                  } finally {
                    setDownloadingAnnotated(false)
                  }
                }}
              >
                <FileSearch className="h-4 w-4" />
                Export Annotated PDF
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/upload">
                  <Upload className="h-4 w-4" />
                  New Upload
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Stats strip */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="relative rounded-2xl border border-border/30 overflow-hidden bg-gradient-to-br from-card via-card/95 to-card/80"
        >
          {/* Ambient glow — hue shifts with pass rate */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{
              background: `radial-gradient(ellipse at 10% 50%, ${rateColor(passRate)} 0%, transparent 55%), radial-gradient(ellipse at 90% 30%, oklch(0.55 0.15 25 / 0.3), transparent 55%)`,
            }}
          />

          <div
            className={cn(
              'relative grid divide-x divide-border/15',
              panelOpen ? 'grid-cols-3' : 'grid-cols-3 sm:grid-cols-5',
            )}
          >
            {/* ─ Pass rate hero ─ */}
            <div className="relative flex items-center gap-4 p-4 sm:p-5 row-span-2 sm:row-span-1 overflow-hidden">
              {/* Subtle background gradient matching pass rate */}
              <div
                className="pointer-events-none absolute inset-0 opacity-[0.07]"
                style={{
                  background: `linear-gradient(135deg, ${rateColor(passRate)}, transparent 70%)`,
                }}
              />

              <div className="relative">
                {/* Outer glow ring */}
                <div
                  className="absolute -inset-1 rounded-full blur-md opacity-25"
                  style={{ backgroundColor: rateColor(passRate) }}
                />
                <div className="relative w-14 h-14 sm:w-[4.5rem] sm:h-[4.5rem]">
                  <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                    {/* Background track */}
                    <circle
                      cx="50"
                      cy="50"
                      r="42"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="5"
                      className="text-border/15"
                    />
                    {/* Animated arc — color from pass rate */}
                    <motion.circle
                      cx="50"
                      cy="50"
                      r="42"
                      fill="none"
                      strokeWidth="6"
                      strokeLinecap="round"
                      stroke={rateColor(passRate)}
                      strokeDasharray={`${2 * Math.PI * 42}`}
                      initial={hasAnimated.current ? false : { strokeDashoffset: 2 * Math.PI * 42 }}
                      animate={{ strokeDashoffset: 2 * Math.PI * 42 * (1 - passRate / 100) }}
                      transition={
                        hasAnimated.current
                          ? { duration: 0 }
                          : { delay: 0.3, duration: 1.2, ease: 'easeOut' }
                      }
                      onAnimationComplete={() => {
                        hasAnimated.current = true
                      }}
                      style={{
                        filter: `drop-shadow(0 0 8px ${rateColor(passRate)}80)`,
                      }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span
                      className="font-display text-lg sm:text-xl font-extrabold leading-none tracking-tight"
                      style={{ color: rateColor(passRate) }}
                    >
                      {passRate}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="relative z-[1]">
                <p className="text-sm font-bold text-foreground leading-tight">
                  {summary.passed_checks}
                  <span className="text-muted-foreground/40 font-normal">
                    /{summary.rules_executed}
                  </span>
                </p>
                <p
                  className="text-[11px] font-semibold mt-0.5"
                  style={{ color: rateColor(passRate) }}
                >
                  {passRate === 100
                    ? 'Perfect'
                    : passRate >= 95
                      ? 'Almost There'
                      : passRate >= 85
                        ? 'Needs Fixes'
                        : passRate >= 70
                          ? 'Review Required'
                          : 'Critical'}
                </p>
                <p className="text-[9px] text-muted-foreground/40 mt-0.5 uppercase tracking-widest font-medium">
                  checks passed
                </p>
              </div>
            </div>

            {/* Metric cells */}
            <MetricCell
              label="Passed"
              value={summary.passed_checks}
              icon={CheckCircle2}
              color="emerald"
              delay={0.15}
              onClick={() => toggleSection('passed')}
              active={openSections.passed}
            />
            <MetricCell
              label="Errors"
              value={summary.errors}
              icon={AlertCircle}
              color="red"
              delay={0.2}
              onClick={() => toggleSection('error')}
              active={openSections.error}
            />
            <MetricCell
              label="Warnings"
              value={summary.warnings}
              icon={AlertTriangle}
              color="amber"
              delay={0.25}
              onClick={() => toggleSection('warning')}
              active={openSections.warning}
            />
            <MetricCell
              label="Info"
              value={summary.infos}
              icon={Info}
              color="sky"
              delay={0.3}
              onClick={() => toggleSection('info')}
              active={openSections.info}
            />
          </div>

          {/* Distribution bar */}
          {(() => {
            const total =
              summary.passed_checks + summary.errors + summary.warnings + summary.infos || 1
            return (
              <div className="flex h-1">
                {summary.passed_checks > 0 && (
                  <motion.div
                    className="bg-emerald-500"
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(summary.passed_checks / total) * 100}%`,
                    }}
                    transition={{ delay: 0.6, duration: 0.8, ease: 'easeOut' }}
                  />
                )}
                {summary.errors > 0 && (
                  <motion.div
                    className="bg-red-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${(summary.errors / total) * 100}%` }}
                    transition={{ delay: 0.7, duration: 0.8, ease: 'easeOut' }}
                  />
                )}
                {summary.warnings > 0 && (
                  <motion.div
                    className="bg-amber-500"
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(summary.warnings / total) * 100}%`,
                    }}
                    transition={{ delay: 0.8, duration: 0.8, ease: 'easeOut' }}
                  />
                )}
                {summary.infos > 0 && (
                  <motion.div
                    className="bg-sky-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${(summary.infos / total) * 100}%` }}
                    transition={{ delay: 0.9, duration: 0.8, ease: 'easeOut' }}
                  />
                )}
              </div>
            )
          })()}
        </motion.div>

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
        <IssueSection
          severity="info"
          issues={infoIssues}
          open={openSections.info}
          onToggle={() => toggleSection('info')}
        />

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
            <span className="text-xs text-muted-foreground ml-1 hidden md:inline truncate">
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

        {/* Scroll-to-top button */}
        <AnimatePresence>
          {showScrollTop && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              onClick={() => leftPanelRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
              className="sticky bottom-3 ml-auto mr-2 z-10 flex items-center justify-center w-8 h-8 rounded-full border border-border/50 bg-card/90 backdrop-blur-sm shadow-lg text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors"
              aria-label="Scroll to top"
            >
              <ChevronUp className="h-4 w-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Right Panel: Document Preview + Chat ── */}
      <AnimatePresence>
        {panelOpen && data && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="flex-1 min-h-0 lg:border-l border-border/50 flex flex-col overflow-hidden bg-card/30"
          >
            {/* Panel tabs — desktop only (mobile uses top bar) */}
            <div className="hidden lg:flex items-center border-b border-border/50 shrink-0">
              <button
                onClick={() => setPanelTab('preview')}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2',
                  panelTab === 'preview'
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                <FileText className="h-3.5 w-3.5" />
                Preview
              </button>
              <button
                onClick={() => setPanelTab('chat')}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2',
                  panelTab === 'chat'
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                AI Chat
              </button>
              <div className="flex-1" />
              <button
                onClick={() => setPanelOpen(false)}
                className="p-2 mr-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                title="Close panel"
              >
                <PanelRightClose className="h-4 w-4" />
              </button>
            </div>

            {/* Panel content — both tabs stay mounted to preserve chat state */}
            <div className="flex-1 min-h-0 relative">
              <div
                className={cn(
                  'absolute inset-0',
                  panelTab !== 'preview' && 'invisible pointer-events-none',
                )}
              >
                <DocumentPreview uploadId={data.upload_id} onContentLoaded={handleContentLoaded} />
              </div>
              <div
                className={cn(
                  'absolute inset-0',
                  panelTab !== 'chat' && 'invisible pointer-events-none',
                )}
              >
                {docContent ? (
                  <DocumentChat documentContent={docContent} filename={docFilename} />
                ) : (
                  <div className="flex items-center justify-center h-full text-xs text-muted-foreground p-4 text-center">
                    Switch to Preview tab first to load the document content.
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Panel toggle button (when closed) — desktop only */}
      {!panelOpen && data && (
        <motion.button
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => setPanelOpen(true)}
          className="hidden lg:flex fixed right-4 top-1/2 -translate-y-1/2 z-30 items-center gap-1.5 px-2 py-3 rounded-lg border border-border/50 bg-card shadow-lg text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all"
          title="Open document panel"
        >
          <PanelRightOpen className="h-4 w-4" />
        </motion.button>
      )}
    </div>
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
        <span className="text-xs text-muted-foreground ml-1 hidden md:inline truncate">
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
              {issues.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-lg border',
                    config.border,
                    config.bg,
                  )}
                >
                  <SevIcon className={cn('h-4 w-4 shrink-0', config.color)} />
                  <p className="text-sm text-muted-foreground">
                    No {config.label.toLowerCase()} for this document.
                  </p>
                </motion.div>
              ) : (
                [...ruleGroups.entries()].map(([ruleId, group], gi) => (
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
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ─── Rate → color (red → amber → emerald) ───────────── */

function rateColor(rate: number): string {
  // Only 100% is green. Everything else shifts red → amber.
  // oklch hue: 30 (red) → 70 (orange) → 100 (amber) → 155 (emerald at 100% only)
  if (rate === 100) return 'oklch(0.72 0.2 155)'
  // 0-99%: red → amber (never reaches green)
  const hue = 30 + (rate / 99) * 70 // 30 → 100
  const chroma = 0.2
  const lightness = 0.6 + (rate / 99) * 0.08
  return `oklch(${lightness} ${chroma} ${hue})`
}

/* ─── Animated counter ────────────────────────────────── */

function AnimatedNumber({ value, delay = 0 }: { value: number; delay?: number }) {
  const [display, setDisplay] = useState(0)
  const hasRun = useRef(false)

  useEffect(() => {
    if (hasRun.current) {
      setDisplay(value)
      return
    }
    if (value === 0) {
      setDisplay(0)
      hasRun.current = true
      return
    }
    const timeout = setTimeout(() => {
      const duration = 900
      const start = performance.now()
      const step = (now: number) => {
        const progress = Math.min((now - start) / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setDisplay(Math.round(eased * value))
        if (progress < 1) requestAnimationFrame(step)
        else hasRun.current = true
      }
      requestAnimationFrame(step)
    }, delay * 1000)
    return () => clearTimeout(timeout)
  }, [value, delay])

  return <span>{display}</span>
}

/* ─── Metric cell ────────────────────────────────────── */

const METRIC_COLORS = {
  emerald: {
    glow: 'bg-emerald-400/20',
    text: 'text-emerald-400',
    iconBg: 'bg-emerald-500/10',
    iconBorder: 'border-emerald-500/25',
    activeBg: 'bg-emerald-500/5',
    activeBorder: 'border-emerald-500/30',
  },
  red: {
    glow: 'bg-red-400/20',
    text: 'text-red-400',
    iconBg: 'bg-red-500/10',
    iconBorder: 'border-red-500/25',
    activeBg: 'bg-red-500/5',
    activeBorder: 'border-red-500/30',
  },
  amber: {
    glow: 'bg-amber-400/20',
    text: 'text-amber-400',
    iconBg: 'bg-amber-500/10',
    iconBorder: 'border-amber-500/25',
    activeBg: 'bg-amber-500/5',
    activeBorder: 'border-amber-500/30',
  },
  sky: {
    glow: 'bg-sky-400/20',
    text: 'text-sky-400',
    iconBg: 'bg-sky-500/10',
    iconBorder: 'border-sky-500/25',
    activeBg: 'bg-sky-500/5',
    activeBorder: 'border-sky-500/30',
  },
} as const

function MetricCell({
  label,
  value,
  icon: Icon,
  color,
  onClick,
  active,
  delay = 0,
}: {
  label: string
  value: number
  icon: typeof CheckCircle2
  color: keyof typeof METRIC_COLORS
  onClick?: () => void
  active?: boolean
  delay?: number
}) {
  const c = METRIC_COLORS[color]
  return (
    <motion.button
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay, duration: 0.4 }}
      onClick={onClick}
      className={cn(
        'relative flex flex-col items-center justify-center gap-1 p-3 sm:p-4 transition-all duration-200',
        'hover:bg-white/[0.02] active:scale-[0.97]',
        'focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:outline-none',
        active && cn(c.activeBg, 'border-t-2', c.activeBorder),
        !active && 'border-t-2 border-transparent',
      )}
    >
      {/* Icon with glow ring */}
      <div className="relative mb-1.5">
        {value > 0 && (
          <motion.div
            className={cn('absolute -inset-1.5 rounded-full', c.glow)}
            animate={{ scale: [1, 1.6, 1], opacity: [0.3, 0, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
        <div
          className={cn(
            'relative w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center',
            'border transition-colors',
            value > 0 ? cn(c.iconBg, c.iconBorder) : 'bg-muted/20 border-border/20',
          )}
        >
          <Icon
            className={cn(
              'h-4 w-4 sm:h-[1.125rem] sm:w-[1.125rem]',
              value > 0 ? c.text : 'text-muted-foreground/25',
            )}
          />
        </div>
      </div>

      {/* Animated number */}
      <p
        className={cn(
          'font-display text-2xl sm:text-3xl font-extrabold leading-none tracking-tight',
          value > 0 ? 'text-foreground' : 'text-muted-foreground/40',
        )}
      >
        <AnimatedNumber value={value} delay={delay} />
      </p>

      {/* Label */}
      <p
        className={cn(
          'text-[10px] sm:text-[11px] font-medium uppercase tracking-wider mt-0.5',
          active ? c.text : 'text-muted-foreground/60',
        )}
      >
        {label}
      </p>
    </motion.button>
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
          <p className="text-xs sm:text-sm text-foreground leading-relaxed break-words">
            {issue.message}
          </p>
          <div className="grid grid-cols-[auto_auto] sm:flex sm:flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
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
