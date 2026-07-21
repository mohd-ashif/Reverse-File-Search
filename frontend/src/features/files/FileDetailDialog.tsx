import { useEffect, useState } from "react";
import { ExternalLink, MessageSquare } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getFileContentUrl } from "@/api/files";
import { ActionItemsSection } from "@/features/files/ActionItemsSection";
import { ContractRiskSection } from "@/features/files/ContractRiskSection";
import { FileChatPanel } from "@/features/files/FileChatPanel";
import { FileSummarySection } from "@/features/files/FileSummarySection";
import { TagBadge } from "@/features/files/TagBadge";
import { useExtractedText, useFileTags } from "@/hooks/useFiles";
import { FILE_STATUS_LABEL, FILE_STATUS_VARIANT, formatBytes, formatDate } from "@/lib/status";
import type { IndexedFile } from "@/types/file";

interface FileDetailDialogProps {
  file: IndexedFile | null;
  onOpenChange: (open: boolean) => void;
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="col-span-2 break-all">{value}</dd>
    </div>
  );
}

export function FileDetailDialog({ file, onOpenChange }: FileDetailDialogProps) {
  const { data: fileTags } = useFileTags(file?.id ?? null);
  const { data: extractedText } = useExtractedText(file?.file_type === "image" ? file.id : null);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setChatOpen(false);
  }, [file?.id]);

  return (
    <Dialog open={file !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        {file ? (
          <>
            <DialogHeader>
              <DialogTitle className="break-all">{file.filename}</DialogTitle>
              <DialogDescription>File details and indexing metadata</DialogDescription>
            </DialogHeader>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="w-fit" asChild>
                <a href={getFileContentUrl(file.id)} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="size-4" />
                  View File
                </a>
              </Button>
              <Button
                variant={chatOpen ? "default" : "outline"}
                size="sm"
                className="w-fit"
                onClick={() => setChatOpen((prev) => !prev)}
              >
                <MessageSquare className="size-4" />
                {chatOpen ? "Details" : "Chat"}
              </Button>
            </div>

            {chatOpen ? (
              <FileChatPanel key={file.id} fileId={file.id} filename={file.filename} />
            ) : (
              <>
                <dl className="divide-y">
                  <DetailRow label="Status" value={<Badge variant={FILE_STATUS_VARIANT[file.status]}>{FILE_STATUS_LABEL[file.status]}</Badge>} />
                  <DetailRow label="Type" value={file.file_type.toUpperCase()} />
                  <DetailRow label="Size" value={formatBytes(file.size_bytes)} />
                  <DetailRow label="Path" value={<span className="font-mono text-xs">{file.absolute_path}</span>} />
                  <DetailRow label="Checksum" value={<span className="font-mono text-xs">{file.checksum}</span>} />
                  <DetailRow label="Folder ID" value={file.folder_id} />
                  <DetailRow label="Created" value={formatDate(file.created_at)} />
                  <DetailRow label="Updated" value={formatDate(file.updated_at)} />
                  {file.file_type === "image" ? (
                    <DetailRow
                      label="OCR"
                      value={
                        <Badge variant={extractedText?.was_corrected ? "success" : "secondary"}>
                          {extractedText?.was_corrected ? "Mistakes corrected" : "Not corrected"}
                        </Badge>
                      }
                    />
                  ) : null}
                  {fileTags && fileTags.tags.length > 0 ? (
                    <DetailRow
                      label="Tags"
                      value={
                        <div className="flex flex-wrap gap-1">
                          {fileTags.tags.map((t) => (
                            <TagBadge key={t} tag={t} />
                          ))}
                        </div>
                      }
                    />
                  ) : null}
                  {file.error_message ? (
                    <DetailRow
                      label="Error"
                      value={<span className="text-destructive">{file.error_message}</span>}
                    />
                  ) : null}
                </dl>

                <FileSummarySection fileId={file.id} />
                <ContractRiskSection fileId={file.id} />
                <ActionItemsSection fileId={file.id} />
              </>
            )}
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
