/** Right-side sheet — upload history with animated list & rich cards. */

import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import {
  FileText,
  FileSpreadsheet,
  FileJson,
  FileType2,
  FileCode,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  Clock,
  ArrowRight,
  Rows3,
  History,
} from 'lucide-react'
import { listUploads, triggerValidation } from '@/api'
import type { UploadHistoryItem, ValidationRunBrief } from '@/types'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const FORMAT_META: Record<string, { icon: typeof FileText; color: string; bg: string }> = {
  csv: { icon: FileText, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  xlsx: { icon: FileSpreadsheet, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  json: { icon: FileJson, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  xml: { icon: FileCode, color: 'text-sky-400', bg: 'bg-sky-500/10' },
  pdf: { icon: FileType2, color: 'text-red-400', bg: 'bg-red-500/10' },
}

const DEFAULT_FMT = { icon: FileText, color: 'text-primary', bg: 'bg-primary/10' }

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function HistorySheet({ open, onOpenChange }: Props) {
  const [uploads, setUploads] = useState<UploadHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [revalidating, setRevalidating] = useState<string | null>(null)
  const navigate = useNavigate()

  const refresh = useCallback(() => {
    setLoading(true)
    listUploads()
      .then(setUploads)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (open) refresh()
  }, [open, refresh])

  async function handleRevalidate(uploadId: string) {
    setRevalidating(uploadId)
    try {
      const run = await triggerValidation(uploadId)
      onOpenChange(false)
      navigate(`/results/${run.validation_id}`)
    } catch {
      /* ignore */
    } finally {
      setRevalidating(null)
    }
  }

  function handleViewResult(validationId: string) {
    onOpenChange(false)
    navigate(`/results/${validationId}`)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent
        side="right"
        className="flex flex-col w-full sm:max-w-md border-l border-border/50 bg-background/95 backdrop-blur-xl"
        showCloseButton={false}
        showOverlay={false}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <SheetHeader className="pb-4 border-b border-border/40">
          <SheetTitle className="flex items-center gap-2 text-base font-display">
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
              <History className="h-3.5 w-3.5 text-primary" />
            </div>
            Upload History
          </SheetTitle>
          <SheetDescription className="text-xs">
            Previous files and validation runs
          </SheetDescription>
        </SheetHeader>

        {loading && uploads.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <Spinner className="h-6 w-6" />
            <p className="text-xs text-muted-foreground animate-pulse">Loading history…</p>
          </div>
        ) : uploads.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <div className="w-14 h-14 rounded-2xl bg-muted/30 flex items-center justify-center">
              <Clock className="h-7 w-7 text-muted-foreground/50" />
            </div>
            <p className="text-sm font-medium">No uploads yet</p>
            <p className="text-xs text-muted-foreground/70">Validated files will appear here</p>
          </div>
        ) : (
          <ScrollArea className="flex-1 min-h-0 -mx-4 -mb-4 mt-2">
            <div className="space-y-2 px-4 pb-4">
              <AnimatePresence initial={false}>
                {uploads.map((upload, i) => (
                  <motion.div
                    key={upload.upload_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ delay: Math.min(i * 0.04, 0.2), duration: 0.3 }}
                  >
                    <UploadItem
                      upload={upload}
                      revalidating={revalidating === upload.upload_id}
                      onRevalidate={() => handleRevalidate(upload.upload_id)}
                      onViewResult={handleViewResult}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>
        )}
      </SheetContent>
    </Sheet>
  )
}

/* ─── Upload item card ────────────────────────────────── */

function UploadItem({
  upload,
  revalidating,
  onRevalidate,
  onViewResult,
}: {
  upload: UploadHistoryItem
  revalidating: boolean
  onRevalidate: () => void
  onViewResult: (validationId: string) => void
}) {
  const fmt = FORMAT_META[upload.file_format] ?? DEFAULT_FMT
  const Icon = fmt.icon
  const latest = upload.validations[0] as ValidationRunBrief | undefined
  const isClean =
    latest?.status === 'completed' &&
    latest.errors === 0 &&
    latest.warnings === 0 &&
    latest.infos === 0

  return (
    <div className="group rounded-xl border border-border/50 bg-card/80 hover:bg-card transition-colors overflow-hidden">
      {/* File info */}
      <div className="p-3 flex items-start gap-3">
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', fmt.bg)}>
          <Icon className={cn('h-4 w-4', fmt.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate leading-tight">
            {upload.filename}
          </p>
          <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
            <span className="uppercase font-mono tracking-wider text-[10px] px-1.5 py-0.5 rounded bg-muted/40">
              {upload.file_format}
            </span>
            {upload.row_count != null && (
              <span className="flex items-center gap-0.5">
                <Rows3 className="h-2.5 w-2.5" />
                {upload.row_count}
              </span>
            )}
            <span className="ml-auto text-muted-foreground/60">
              {relativeTime(upload.uploaded_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Latest validation result */}
      {latest && latest.status === 'completed' && (
        <div
          className="mx-3 mb-2 flex items-center gap-2 text-xs cursor-pointer rounded-lg bg-muted/30 px-3 py-2 hover:bg-muted/50 transition-colors"
          onClick={() => onViewResult(latest.validation_id)}
        >
          {isClean ? (
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              All passed
            </span>
          ) : (
            <div className="flex items-center gap-3">
              {latest.errors > 0 && (
                <span className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3 text-red-400" />
                  <span className="text-foreground font-mono">{latest.errors}</span>
                </span>
              )}
              {latest.warnings > 0 && (
                <span className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                  <span className="text-foreground font-mono">{latest.warnings}</span>
                </span>
              )}
              {latest.infos > 0 && (
                <span className="flex items-center gap-1">
                  <Info className="h-3 w-3 text-sky-400" />
                  <span className="text-foreground font-mono">{latest.infos}</span>
                </span>
              )}
            </div>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            {upload.validations.length > 1 && (
              <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0">
                {upload.validations.length}×
              </Badge>
            )}
            <ArrowRight className="h-3 w-3 text-muted-foreground/40 group-hover:text-primary transition-colors" />
          </div>
        </div>
      )}

      {latest && latest.status !== 'completed' && (
        <div className="mx-3 mb-2 flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
          <Spinner className="h-3 w-3" />
          <span className="capitalize">{latest.status}…</span>
        </div>
      )}

      {/* Re-validate */}
      <div className="border-t border-border/30 px-3 py-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full h-7 text-xs text-muted-foreground hover:text-foreground gap-1.5"
          onClick={onRevalidate}
          disabled={revalidating}
        >
          {revalidating ? (
            <>
              <Spinner className="h-3 w-3" />
              Validating…
            </>
          ) : (
            <>
              <RotateCw className="h-3 w-3" />
              Re-validate
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
