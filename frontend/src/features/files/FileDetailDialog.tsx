import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { FileSummarySection } from "@/features/files/FileSummarySection";
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
  return (
    <Dialog open={file !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        {file ? (
          <>
            <DialogHeader>
              <DialogTitle className="break-all">{file.filename}</DialogTitle>
              <DialogDescription>File details and indexing metadata</DialogDescription>
            </DialogHeader>
            <dl className="divide-y">
              <DetailRow label="Status" value={<Badge variant={FILE_STATUS_VARIANT[file.status]}>{FILE_STATUS_LABEL[file.status]}</Badge>} />
              <DetailRow label="Type" value={file.file_type.toUpperCase()} />
              <DetailRow label="Size" value={formatBytes(file.size_bytes)} />
              <DetailRow label="Path" value={<span className="font-mono text-xs">{file.absolute_path}</span>} />
              <DetailRow label="Checksum" value={<span className="font-mono text-xs">{file.checksum}</span>} />
              <DetailRow label="Folder ID" value={file.folder_id} />
              <DetailRow label="Created" value={formatDate(file.created_at)} />
              <DetailRow label="Updated" value={formatDate(file.updated_at)} />
              {file.error_message ? (
                <DetailRow
                  label="Error"
                  value={<span className="text-destructive">{file.error_message}</span>}
                />
              ) : null}
            </dl>

            <FileSummarySection fileId={file.id} />
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
