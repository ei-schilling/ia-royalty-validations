/** Right-side sheet displaying upload history with re-validation support. */

import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  FileSpreadsheet,
  FileJson,
  FileType2,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  Clock,
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
import { Separator } from '@/components/ui/separator'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const FORMAT_ICON: Record<string, typeof FileText> = {
  csv: FileText,
  xlsx: FileSpreadsheet,
  json: FileJson,
  pdf: FileType2,
}

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
        className="flex flex-col w-full sm:max-w-md"
        showCloseButton={false}
        showOverlay={false}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <SheetHeader>
          <SheetTitle>Upload History</SheetTitle>
          <SheetDescription>
            Previously uploaded files and their validation results.
          </SheetDescription>
        </SheetHeader>

        <Separator />

        {loading && uploads.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <Spinner className="h-6 w-6" />
          </div>
        ) : uploads.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
            <Clock className="h-8 w-8" />
            <p className="text-sm">No uploads yet</p>
          </div>
        ) : (
          <ScrollArea className="flex-1 -mx-4">
            <div className="space-y-1 px-4">
              {uploads.map((upload) => (
                <UploadItem
                  key={upload.upload_id}
                  upload={upload}
                  revalidating={revalidating === upload.upload_id}
                  onRevalidate={() => handleRevalidate(upload.upload_id)}
                  onViewResult={handleViewResult}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </SheetContent>
    </Sheet>
  )
}

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
  const Icon = FORMAT_ICON[upload.file_format] ?? FileText
  const latest = upload.validations[0] as ValidationRunBrief | undefined

  return (
    <div className="rounded-lg border border-border bg-card p-3 space-y-2.5">
      {/* File info row */}
      <div className="flex items-start gap-2.5">
        <div className="rounded-md bg-primary/10 p-1.5 mt-0.5">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{upload.filename}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
            <span className="uppercase font-mono">{upload.file_format}</span>
            {upload.row_count != null && (
              <>
                <span>&middot;</span>
                <span>{upload.row_count} rows</span>
              </>
            )}
            <span>&middot;</span>
            <span>{relativeTime(upload.uploaded_at)}</span>
          </div>
        </div>
      </div>

      {/* Latest validation result */}
      {latest && latest.status === 'completed' && (
        <div
          className="flex items-center gap-3 text-xs cursor-pointer rounded-md bg-muted/50 px-2.5 py-1.5 hover:bg-muted transition-colors"
          onClick={() => onViewResult(latest.validation_id)}
        >
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
            <span className="text-muted-foreground">Pass</span>
          </span>
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
          {latest.errors === 0 && latest.warnings === 0 && latest.infos === 0 && (
            <span className="text-emerald-400">All checks passed</span>
          )}
          {upload.validations.length > 1 && (
            <Badge variant="secondary" className="ml-auto text-[10px]">
              {upload.validations.length} runs
            </Badge>
          )}
        </div>
      )}

      {latest && latest.status !== 'completed' && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md px-2.5 py-1.5">
          <Spinner className="h-3 w-3" />
          <span className="capitalize">{latest.status}</span>
        </div>
      )}

      {/* Re-validate button */}
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={onRevalidate}
        disabled={revalidating}
      >
        {revalidating ? (
          <>
            <Spinner className="h-3.5 w-3.5" />
            Validating…
          </>
        ) : (
          <>
            <RotateCw className={cn('h-3.5 w-3.5')} />
            Re-validate
          </>
        )}
      </Button>
    </div>
  )
}
