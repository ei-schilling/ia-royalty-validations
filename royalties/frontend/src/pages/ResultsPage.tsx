/** Validation results page — displays summary and issue details. */

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { AlertCircle, AlertTriangle, Info, CheckCircle2, Upload } from 'lucide-react'
import { getValidation } from '@/api'
import type { ValidationRunResponse, ValidationIssueSummary } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const SEVERITY_CONFIG = {
  error: { icon: AlertCircle, color: 'error' as const, label: 'Errors' },
  warning: { icon: AlertTriangle, color: 'warning' as const, label: 'Warnings' },
  info: { icon: Info, color: 'info' as const, label: 'Info' },
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
      <Card className="p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-500 mb-3" />
        <p className="text-sm text-red-600">{error}</p>
        <Link to="/upload" className="mt-4 inline-block">
          <Button variant="secondary">Back to Upload</Button>
        </Link>
      </Card>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="h-8 w-8" />
      </div>
    )
  }

  const { summary, issues } = data
  const filtered = filter ? issues.filter((i) => i.severity === filter) : issues

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-ink-900">Validation Results</h1>
          <p className="text-sm text-ink-500 mt-1">
            {summary.rules_executed} rules executed &middot; {summary.total_rows} rows analyzed
          </p>
        </div>
        <Link to="/upload">
          <Button variant="secondary">
            <Upload className="h-4 w-4" /> New Upload
          </Button>
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <SummaryCard
          label="Passed"
          value={summary.passed_checks}
          icon={CheckCircle2}
          color="text-emerald-600"
          bg="bg-emerald-50"
        />
        <SummaryCard
          label="Errors"
          value={summary.errors}
          icon={AlertCircle}
          color="text-red-600"
          bg="bg-red-50"
          onClick={() => setFilter(filter === 'error' ? null : 'error')}
          active={filter === 'error'}
        />
        <SummaryCard
          label="Warnings"
          value={summary.warnings}
          icon={AlertTriangle}
          color="text-amber-600"
          bg="bg-amber-50"
          onClick={() => setFilter(filter === 'warning' ? null : 'warning')}
          active={filter === 'warning'}
        />
        <SummaryCard
          label="Info"
          value={summary.infos}
          icon={Info}
          color="text-sky-600"
          bg="bg-sky-50"
          onClick={() => setFilter(filter === 'info' ? null : 'info')}
          active={filter === 'info'}
        />
      </div>

      {/* Issues list */}
      {filtered.length === 0 ? (
        <Card className="p-8 text-center">
          <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-3" />
          <p className="text-ink-600 font-medium">
            {filter ? 'No issues at this severity level' : 'No issues found — all checks passed!'}
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-ink-400 font-mono">
            {filtered.length} issue{filtered.length !== 1 ? 's' : ''}
            {filter && ` (${filter})`}
          </p>
          {filtered.map((issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Summary card ───────────────────────────────────────────────── */

function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
  bg,
  onClick,
  active,
}: {
  label: string
  value: number
  icon: typeof CheckCircle2
  color: string
  bg: string
  onClick?: () => void
  active?: boolean
}) {
  return (
    <Card
      className={cn(
        'p-4 flex items-center gap-3 transition-all',
        onClick && 'cursor-pointer hover:shadow-md',
        active && 'ring-2 ring-brand-500 ring-offset-2',
      )}
    >
      <div className={cn('rounded-lg p-2', bg)} onClick={onClick}>
        <Icon className={cn('h-5 w-5', color)} />
      </div>
      <div onClick={onClick}>
        <p className="text-2xl font-bold text-ink-900 font-mono">{value}</p>
        <p className="text-xs text-ink-500">{label}</p>
      </div>
    </Card>
  )
}

/* ─── Issue card ─────────────────────────────────────────────────── */

function IssueCard({ issue }: { issue: ValidationIssueSummary }) {
  const config = SEVERITY_CONFIG[issue.severity]
  const SevIcon = config.icon

  return (
    <Card className="p-4 flex gap-3">
      <div className="pt-0.5">
        <Badge variant={config.color}>
          <SevIcon className="h-3 w-3 mr-1" />
          {issue.severity}
        </Badge>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-ink-800 font-medium">{issue.message}</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs text-ink-400">
          <span className="font-mono">{issue.rule_id}</span>
          {issue.row_number != null && <span>Row {issue.row_number}</span>}
          {issue.field && <span>Field: {issue.field}</span>}
          {issue.expected_value && (
            <span>
              Expected: <span className="text-ink-600">{issue.expected_value}</span>
            </span>
          )}
          {issue.actual_value && (
            <span>
              Actual: <span className="text-ink-600">{issue.actual_value}</span>
            </span>
          )}
        </div>
      </div>
    </Card>
  )
}
