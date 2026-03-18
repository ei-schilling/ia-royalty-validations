/** Upload page — immersive drag-and-drop with file preview. */

import { useState, useRef, useCallback, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import {
  Upload,
  FileText,
  FileSpreadsheet,
  FileJson,
  FileType2,
  CloudUpload,
  X,
  Sparkles,
  ArrowRight,
} from 'lucide-react'
import { uploadFile, triggerValidation } from '@/api'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

const ICON_MAP: Record<string, typeof FileText> = {
  csv: FileText,
  xlsx: FileSpreadsheet,
  json: FileJson,
  pdf: FileType2,
}

const FORMAT_COLORS: Record<string, string> = {
  csv: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30',
  xlsx: 'from-blue-500/20 to-blue-500/5 border-blue-500/30',
  json: 'from-amber-500/20 to-amber-500/5 border-amber-500/30',
  pdf: 'from-red-500/20 to-red-500/5 border-red-500/30',
}

const FORMAT_TEXT: Record<string, string> = {
  csv: 'text-emerald-400',
  xlsx: 'text-blue-400',
  json: 'text-amber-400',
  pdf: 'text-red-400',
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState<'uploading' | 'validating' | null>(null)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const ext = file?.name.split('.').pop()?.toLowerCase() ?? ''
  const FileIcon = ICON_MAP[ext] ?? FileText

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      setProgress('uploading')
      const upload = await uploadFile(file)
      setProgress('validating')
      const run = await triggerValidation(upload.upload_id)
      navigate(`/results/${run.validation_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setProgress(null)
    } finally {
      setUploading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 max-w-2xl mx-auto"
    >
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2.5">
          <Upload className="h-6 w-6 text-primary" />
          Upload Statement
        </h1>
        <p className="text-sm text-muted-foreground mt-1 ml-[34px]">
          Drag and drop your royalty settlement file to begin validation.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragging(false)}
        onClick={() => !file && inputRef.current?.click()}
        className={cn(
          'group relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden',
          dragging
            ? 'border-primary bg-primary/5 scale-[1.01]'
            : file
              ? 'border-border/50 bg-card'
              : 'border-border/50 hover:border-primary/40 hover:bg-muted/30',
        )}
      >
        {/* Animated grid background */}
        {!file && (
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
        )}

        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="p-8"
            >
              <div
                className={cn(
                  'flex items-center gap-5 px-6 py-5 rounded-xl bg-gradient-to-r border',
                  FORMAT_COLORS[ext] ?? 'from-muted/50 to-muted/20 border-border/50',
                )}
              >
                <div className="w-14 h-14 rounded-xl bg-background/80 flex items-center justify-center shrink-0">
                  <FileIcon className={cn('h-7 w-7', FORMAT_TEXT[ext] ?? 'text-primary')} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground truncate">{file.name}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span
                      className={cn(
                        'font-mono font-semibold uppercase',
                        FORMAT_TEXT[ext] ?? 'text-primary',
                      )}
                    >
                      {ext}
                    </span>
                    <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                    <span>{formatSize(file.size)}</span>
                    <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                    <span>Ready to validate</span>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                    setError('')
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-4 py-16 px-8"
            >
              <motion.div
                animate={dragging ? { scale: 1.1, y: -4 } : { scale: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 300 }}
                className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center"
              >
                <CloudUpload
                  className={cn(
                    'h-8 w-8 transition-colors',
                    dragging ? 'text-primary' : 'text-muted-foreground/50',
                  )}
                />
              </motion.div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">
                  {dragging ? 'Drop your file here' : 'Drop a file here or'}{' '}
                  {!dragging && (
                    <span className="text-primary font-semibold cursor-pointer hover:underline underline-offset-4">
                      browse
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Supports CSV, XLSX, JSON, and PDF up to 50 MB
                </p>
              </div>
              {/* Format badges */}
              <div className="flex items-center gap-2 mt-2">
                {['CSV', 'XLSX', 'JSON', 'PDF'].map((fmt) => (
                  <span
                    key={fmt}
                    className="px-2.5 py-1 rounded-md bg-muted/50 text-[10px] font-mono font-semibold text-muted-foreground/70 uppercase"
                  >
                    {fmt}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.json,.pdf"
          className="hidden"
          onChange={(e) => {
            const selected = e.target.files?.[0]
            if (selected) setFile(selected)
          }}
        />
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-2.5"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Upload button */}
      <Button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="w-full h-12 text-base font-semibold gap-2.5 group"
      >
        {uploading ? (
          <>
            <Spinner className="h-4 w-4" />
            {progress === 'uploading' ? 'Uploading file…' : 'Running validation…'}
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Upload & Validate
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </>
        )}
      </Button>
    </motion.div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
