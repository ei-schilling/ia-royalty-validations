/** Upload page — batch-capable drag-and-drop with animated progress. */

import { motion, AnimatePresence } from 'motion/react'
import { Upload, Sparkles, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  DropZone,
  FileQueueList,
  UploadProgress,
  BatchSummary,
  useFileQueue,
  useBatchUpload,
} from '@/features/uploads'

export default function UploadPage() {
  const queue = useFileQueue()
  const batch = useBatchUpload({
    files: queue.files,
    updateFile: queue.updateFile,
    updateByUploadId: queue.updateByUploadId,
    setAllStatus: queue.setAllStatus,
    setFiles: queue.setFiles,
  })

  const isProcessing = batch.phase === 'uploading' || batch.phase === 'processing'
  const isCompleted = batch.phase === 'completed'

  function handleStartOver() {
    queue.clearFiles()
    batch.reset()
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn(
        'space-y-6 mx-auto w-full flex-1 min-h-0 flex flex-col transition-all duration-500',
        isCompleted ? 'max-w-6xl' : queue.files.length > 0 ? 'max-w-4xl' : 'max-w-2xl',
      )}
    >
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2.5">
          <Upload className="h-6 w-6 text-primary" />
          Upload Statements
        </h1>
        <p className="text-sm text-muted-foreground mt-1 ml-[34px]">
          Drag and drop your royalty settlement files to begin validation.
        </p>
      </div>

      <AnimatePresence mode="wait">
        {/* Phase 1 — File selection (idle) */}
        {!isProcessing && !isCompleted && (
          <motion.div
            key="select"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-4"
          >
            {/* Drop zone */}
            <DropZone
              onFilesAdded={queue.addFiles}
              hasFiles={queue.files.length > 0}
              disabled={isProcessing}
            />

            {/* Top upload button — visible only when files are queued */}
            <AnimatePresence>
              {queue.files.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Button
                    onClick={batch.startBatch}
                    disabled={queue.files.length === 0}
                    className="w-full h-11 text-sm font-semibold gap-2 group"
                  >
                    <Sparkles className="h-4 w-4" />
                    Upload & Validate
                    {queue.files.length > 1 && (
                      <span className="text-primary-foreground/70 font-normal">
                        ({queue.files.length} files)
                      </span>
                    )}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* File queue */}
            <FileQueueList
              files={queue.files}
              onRemove={queue.removeFile}
              onClear={queue.clearFiles}
              disabled={isProcessing}
            />

            {/* Error */}
            <AnimatePresence>
              {batch.error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-2.5"
                >
                  {batch.error}
                </motion.p>
              )}
            </AnimatePresence>

            {/* Upload button */}
            <Button
              onClick={batch.startBatch}
              disabled={queue.files.length === 0}
              className="w-full h-12 text-base font-semibold gap-2.5 group"
            >
              <Sparkles className="h-4 w-4" />
              Upload & Validate
              {queue.files.length > 1 && (
                <span className="text-primary-foreground/70 font-normal">
                  ({queue.files.length} files)
                </span>
              )}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Button>
          </motion.div>
        )}

        {/* Phase 2 — Processing (uploading / validating) */}
        {isProcessing && (
          <motion.div
            key="progress"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
          >
            <UploadProgress phase={batch.phase} files={queue.files} />
          </motion.div>
        )}

        {/* Phase 3 — Completed */}
        {isCompleted && (
          <motion.div
            key="summary"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex-1 min-h-0"
          >
            <BatchSummary
              files={queue.files}
              elapsed={batch.elapsed}
              onStartOver={handleStartOver}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
