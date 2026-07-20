/**
 * components/UploadZone.tsx
 * --------------------------
 * Drag-and-drop PDF upload zone. Handles client-side validation (file
 * type/size), drag visual feedback via Framer Motion, calls the backend
 * /api/analyze endpoint, and reports the result (or an error) up to the
 * parent via callback props. The parent owns what happens next — this
 * component only owns the upload interaction itself.
 */

import { useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, FileText, Loader2, UploadCloud } from "lucide-react";

import { analyzeResume, ApiError, type AnalyzeResponse } from "@/api/client";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB, mirrors the backend limit

interface UploadZoneProps {
  onAnalysisStart?: () => void;
  onAnalysisComplete: (result: AnalyzeResponse) => void;
}

export default function UploadZone({ onAnalysisStart, onAnalysisComplete }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const dragCounter = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!looksLikePdf) {
      return "Only PDF files are supported.";
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return "File is too large. Please upload a PDF under 10 MB.";
    }
    return null;
  };

  const handleFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setErrorMessage(validationError);
        return;
      }

      setErrorMessage(null);
      setFileName(file.name);
      setIsUploading(true);
      onAnalysisStart?.();

      try {
        const result = await analyzeResume(file);
        onAnalysisComplete(result);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
        setErrorMessage(message);
      } finally {
        setIsUploading(false);
      }
    },
    [onAnalysisComplete, onAnalysisStart]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      dragCounter.current = 0;
      setIsDragging(false);

      const file = event.dataTransfer.files?.[0];
      if (file) {
        void handleFile(file);
      }
    },
    [handleFile]
  );

  const handleDragEnter = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragCounter.current += 1;
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      void handleFile(file);
    }
    event.target.value = ""; // allow re-selecting the same file after an error
  };

  return (
    <div className="w-full">
      <motion.div
        onDrop={handleDrop}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onClick={!isUploading ? handleBrowseClick : undefined}
        animate={{
          scale: isDragging ? 1.02 : 1,
          borderColor: isDragging ? "rgba(139,92,246,0.8)" : "rgba(255,255,255,0.15)",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        className={`relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed bg-ink-800/40 px-8 py-16 text-center backdrop-blur-xl transition-colors ${
          isUploading ? "cursor-not-allowed opacity-80" : "hover:border-violet-400/60 hover:bg-ink-800/60"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        <AnimatePresence mode="wait">
          {isUploading ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="flex flex-col items-center gap-4"
            >
              <Loader2 className="h-12 w-12 animate-spin text-violet-400" />
              <div>
                <p className="font-display text-lg font-semibold text-white">Analyzing {fileName}</p>
                <p className="mt-1 text-sm text-mist-400">
                  Extracting skills, scoring your resume, and matching roles — this can take a few seconds.
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="flex flex-col items-center gap-4"
            >
              <motion.div
                animate={{ y: isDragging ? -6 : 0 }}
                className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient shadow-glow"
              >
                {fileName ? (
                  <FileText className="h-8 w-8 text-white" />
                ) : (
                  <UploadCloud className="h-8 w-8 text-white" />
                )}
              </motion.div>
              <div>
                <p className="font-display text-lg font-semibold text-white">
                  {isDragging ? "Drop your resume here" : "Drag & drop your resume"}
                </p>
                <p className="mt-1 text-sm text-mist-400">
                  or <span className="font-medium text-violet-300">browse</span> to upload a PDF (max 10 MB)
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 flex items-start gap-3 rounded-2xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-300"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
