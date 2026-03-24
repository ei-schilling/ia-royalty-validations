/** Document preview — tabular, raw text, XML, or native PDF view. */

import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { FileSpreadsheet, FileText, FileJson, FileType2, FileCode, Rows3, Search } from 'lucide-react'
import { getUploadContent } from '@/api'
import type { UploadContentResponse } from '@/types'
import { Spinner } from '@/components/ui/spinner'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const FORMAT_META: Record<string, { icon: typeof FileText; label: string; color: string }> = {
  csv: { icon: FileSpreadsheet, label: 'CSV', color: 'text-emerald-400' },
  xlsx: { icon: FileSpreadsheet, label: 'Excel', color: 'text-emerald-400' },
  xls: { icon: FileSpreadsheet, label: 'Excel', color: 'text-emerald-400' },
  json: { icon: FileJson, label: 'JSON', color: 'text-amber-400' },
  xml: { icon: FileCode, label: 'XML', color: 'text-sky-400' },
  pdf: { icon: FileType2, label: 'PDF', color: 'text-rose-400' },
}

interface Props {
  uploadId: string
  /** Called when the raw text content is available — used by the chat component. */
  onContentLoaded?: (content: string, filename: string) => void
}

export default function DocumentPreview({ uploadId, onContentLoaded }: Props) {
  const [data, setData] = useState<UploadContentResponse | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')

  // PDF state
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [pdfError, setPdfError] = useState(false)

  useEffect(() => {
    getUploadContent(uploadId)
      .then((d) => {
        setData(d)
        onContentLoaded?.(d.raw, d.filename)
      })
      .catch((err) => setError(err.message))
  }, [uploadId, onContentLoaded])

  // Fetch PDF as blob for native rendering (avoids auth/content-type issues)
  useEffect(() => {
    if (!data || data.format !== 'pdf') return
    const token = localStorage.getItem('rsv_token') || ''
    fetch(`/api/uploads/${uploadId}/file?token=${encodeURIComponent(token)}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load PDF')
        return res.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        setPdfBlobUrl(url)
        setPdfError(false)
      })
      .catch(() => {
        setPdfBlobUrl(null)
        setPdfError(true)
      })
    return () => {
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, uploadId])

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-4 text-sm text-destructive">
        {error}
      </div>
    )
  }
  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2">
        <Spinner className="w-5 h-5" />
        <span className="text-xs text-muted-foreground">Loading preview…</span>
      </div>
    )
  }

  const meta = FORMAT_META[data.format] || {
    icon: FileText,
    label: data.format.toUpperCase(),
    color: 'text-muted-foreground',
  }
  const Icon = meta.icon
  const isTabular = data.headers.length > 0 && data.rows.length > 0
  const isPdf = data.format === 'pdf'

  // Filter rows
  const lowerFilter = filter.toLowerCase()
  const filteredRows = lowerFilter
    ? data.rows.filter((row) => row.some((cell) => cell.toLowerCase().includes(lowerFilter)))
    : data.rows

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50 shrink-0">
        <Icon className={cn('h-4 w-4', meta.color)} />
        <span className="flex-1 text-xs font-medium truncate text-foreground">{data.filename}</span>
        <Badge variant="secondary" className="text-[10px] font-mono">
          {meta.label}
        </Badge>
        {data.total_rows != null && (
          <Badge variant="secondary" className="text-[10px] font-mono gap-1">
            <Rows3 className="h-2.5 w-2.5" />
            {data.total_rows}
          </Badge>
        )}
      </div>

      {/* Search filter for tabular data */}
      {isTabular && !isPdf && (
        <div className="px-3 py-2 border-b border-border/30 shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter rows…"
              className="text-xs h-7 pl-7"
            />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {isPdf ? (
          pdfBlobUrl ? (
            <iframe src={pdfBlobUrl} title={data.filename} className="w-full h-full border-0" />
          ) : pdfError ? (
            <div className="flex items-center justify-center h-full p-4 text-xs text-destructive">
              Failed to load PDF
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <Spinner className="w-5 h-5" />
            </div>
          )
        ) : isTabular ? (
          <table className="w-full text-[11px] border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="bg-muted/80 backdrop-blur-sm">
                <th className="px-2 py-1.5 font-semibold text-muted-foreground border-b border-border/50 w-8 text-center">
                  #
                </th>
                {data.headers.map((h, i) => (
                  <th
                    key={i}
                    className="px-2 py-1.5 text-left font-semibold text-muted-foreground border-b border-border/50 whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, ri) => (
                <motion.tr
                  key={ri}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(ri * 0.005, 0.3) }}
                  className="transition-colors hover:bg-muted/30"
                >
                  <td className="px-2 py-1 font-mono text-center border-b text-muted-foreground/50 border-border/20">
                    {ri + 1}
                  </td>
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-2 py-1 text-foreground/80 border-b border-border/20 whitespace-nowrap max-w-[200px] truncate"
                      title={cell}
                    >
                      {cell}
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        ) : (
          <pre className="p-3 text-[11px] text-foreground/80 font-mono whitespace-pre-wrap leading-relaxed">
            {data.raw || '(No content available)'}
          </pre>
        )}
      </div>
    </div>
  )
}
