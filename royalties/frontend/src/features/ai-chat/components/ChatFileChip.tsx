/** ChatFileChip — file attachment badge with upload status. */

import { motion } from 'motion/react'
import {
  FileText,
  FileSpreadsheet,
  FileJson,
  FileType2,
  CheckCircle2,
  AlertCircle,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const FILE_ICONS: Record<string, typeof FileText> = {
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  json: FileJson,
  pdf: FileType2,
  txt: FileText,
  md: FileText,
  doc: FileText,
  docx: FileText,
}

const FILE_COLORS: Record<string, string> = {
  csv: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  xlsx: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  xls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  json: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  pdf: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  txt: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  md: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  doc: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  docx: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
}

function getFileInfo(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const Icon = FILE_ICONS[ext] || FileText
  const color = FILE_COLORS[ext] || 'text-muted-foreground bg-muted/50 border-border/50'
  return { ext, Icon, color }
}

interface ChatFileChipProps {
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  onRemove?: () => void
}

export function ChatFileChip({ file, status, onRemove }: ChatFileChipProps) {
  const { ext, Icon, color } = getFileInfo(file.name)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: -10 }}
      className={cn('inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs', color)}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="max-w-[140px] truncate font-medium">{file.name}</span>
      <span className="uppercase opacity-60">.{ext}</span>

      {status === 'uploading' && (
        <motion.div
          className="h-3 w-3 rounded-full border-2 border-current border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
        />
      )}
      {status === 'done' && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
      {status === 'error' && <AlertCircle className="h-3 w-3 text-destructive" />}

      {onRemove && status === 'pending' && (
        <button
          onClick={onRemove}
          className="ml-1 hover:text-foreground transition-colors"
          aria-label={`Remove ${file.name}`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </motion.div>
  )
}
