/** Upload page — file upload with drag-and-drop. */

import { useState, useRef, useCallback, type DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, FileSpreadsheet, FileJson, FileType2 } from 'lucide-react'
import { uploadFile, triggerValidation } from '@/api'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'

const ICON_MAP: Record<string, typeof FileText> = {
  csv: FileText,
  xlsx: FileSpreadsheet,
  json: FileJson,
  pdf: FileType2,
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
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
      const upload = await uploadFile(file)
      const run = await triggerValidation(upload.upload_id)
      navigate(`/results/${run.validation_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl text-foreground">Upload Statement</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a CSV, Excel, JSON, or PDF royalty statement file for validation.
        </p>
      </div>

      {/* Drop zone */}
      <Card
        className={`flex flex-col items-center justify-center gap-4 p-12 border-2 border-dashed transition-colors cursor-pointer ${
          dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/60'
        }`}
      >
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragging(false)}
          onClick={() => inputRef.current?.click()}
          className="flex flex-col items-center gap-4 w-full"
        >
          {file ? (
            <>
              <FileIcon className="h-10 w-10 text-primary" />
              <div className="text-center">
                <p className="font-medium text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {(file.size / 1024).toFixed(1)} KB &middot; {ext.toUpperCase()}
                </p>
              </div>
              <Button
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                }}
              >
                Choose different file
              </Button>
            </>
          ) : (
            <>
              <Upload className="h-10 w-10 text-muted-foreground/50" />
              <div className="text-center">
                <p className="text-sm text-muted-foreground">
                  Drop a file here or{' '}
                  <span className="text-primary font-medium underline underline-offset-2">
                    browse
                  </span>
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  CSV, XLSX, JSON, or PDF up to 50 MB
                </p>
              </div>
            </>
          )}
        </div>
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
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button onClick={handleUpload} disabled={!file || uploading} className="w-full">
        {uploading ? (
          <>
            <Spinner className="h-4 w-4" /> Validating…
          </>
        ) : (
          'Upload & Validate'
        )}
      </Button>
    </div>
  )
}
