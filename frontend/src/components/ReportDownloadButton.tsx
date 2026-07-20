/**
 * ReportDownloadButton.tsx
 * --------------------------
 * Button that requests the PDF report from POST /api/report and triggers
 * a browser download. Owns its own loading/error state so it can be
 * dropped anywhere in the dashboard without extra plumbing from parents.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Download, Loader2 } from "lucide-react";
import { downloadReport, type AnalyzeResponse, ApiError } from "@/api/client";

interface ReportDownloadButtonProps {
  analysis: AnalyzeResponse;
}

export default function ReportDownloadButton({ analysis }: ReportDownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);

    try {
      const blob = await downloadReport(analysis);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const safeName = (analysis.resume.name || "resume").replace(/[^a-z0-9]+/gi, "_").toLowerCase();
      link.download = `${safeName}_analysis_report.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "Failed to download the report.";
      setError(message);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex flex-col items-start gap-2">
      <motion.button
        type="button"
        onClick={handleDownload}
        disabled={isDownloading}
        whileHover={{ scale: isDownloading ? 1 : 1.03 }}
        whileTap={{ scale: isDownloading ? 1 : 0.97 }}
        className="btn-primary"
      >
        {isDownloading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating PDF...
          </>
        ) : (
          <>
            <Download className="h-4 w-4" />
            Download Full Report
          </>
        )}
      </motion.button>

      {error && (
        <div className="flex items-center gap-1.5 text-xs text-rose-400">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </div>
      )}
    </div>
  );
}
