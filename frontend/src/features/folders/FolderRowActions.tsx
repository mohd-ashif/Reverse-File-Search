import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { MessageSquare, ScanSearch, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { ScanProgressDialog } from "@/features/folders/ScanProgressDialog";
import { foldersQueryKey, useDeleteFolder, useEstimateFolder, useStartFolderScan } from "@/hooks/useFolders";
import type { Folder } from "@/types/folder";

export function FolderRowActions({ folder }: { folder: Folder }) {
  const queryClient = useQueryClient();
  const startScan = useStartFolderScan();
  const deleteFolder = useDeleteFolder();
  const estimateFolder = useEstimateFolder();
  const [sensitiveWarning, setSensitiveWarning] = useState<{ count: number; samples: string[] } | null>(null);
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  const runScan = (skipSensitive: boolean) => {
    startScan.mutate(
      { folderId: folder.id, skipSensitive },
      {
        onSuccess: ({ scan_id }) => {
          setActiveScanId(scan_id);
          setProgressOpen(true);
        },
        onError: (error) => {
          toast.error("Failed to start scan", { description: error instanceof Error ? error.message : undefined });
        },
      }
    );
  };

  const handleScanFinished = () => {
    void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
    void queryClient.invalidateQueries({ queryKey: ["files"] });
  };

  const handleScan = () => {
    estimateFolder.mutate(
      { path: folder.path },
      {
        onSuccess: (result) => {
          if (result.sensitive_files_detected > 0) {
            setSensitiveWarning({
              count: result.sensitive_files_detected,
              samples: result.sensitive_file_samples,
            });
          } else {
            runScan(true);
          }
        },
        // If the pre-check itself fails, fall back to scanning directly so the
        // scan endpoint's own error handling can surface the real problem.
        onError: () => runScan(true),
      }
    );
  };

  const handleDelete = () => {
    deleteFolder.mutate(folder.id, {
      onSuccess: () => toast.success("Folder removed", { description: folder.path }),
      onError: (error) => {
        toast.error("Failed to remove folder", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  return (
    <div className="flex items-center justify-end gap-2">
      <Button variant="outline" size="sm" aria-label={`Chat with ${folder.path}`} asChild>
        <Link to={`/search?folderId=${folder.id}`}>
          <MessageSquare className="mr-2 h-4 w-4" />
          Chat
        </Link>
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={handleScan}
        disabled={startScan.isPending}
        aria-label={`Scan ${folder.path}`}
      >
        {startScan.isPending ? <Spinner className="mr-2" /> : <ScanSearch className="mr-2 h-4 w-4" />}
        Scan
      </Button>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            disabled={deleteFolder.isPending}
            aria-label={`Remove ${folder.path}`}
          >
            {deleteFolder.isPending ? <Spinner className="mr-2" /> : <Trash2 className="mr-2 h-4 w-4" />}
            Remove
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this folder?</AlertDialogTitle>
            <AlertDialogDescription>
              <span className="font-mono text-xs">{folder.path}</span> will stop being monitored and its
              indexed files will be removed from search. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
            >
              Remove folder
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={sensitiveWarning !== null} onOpenChange={(open) => !open && setSensitiveWarning(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-destructive" />
              Sensitive files detected
            </AlertDialogTitle>
            <AlertDialogDescription>
              {sensitiveWarning?.count} file{sensitiveWarning?.count === 1 ? "" : "s"} in{" "}
              <span className="font-mono text-xs">{folder.path}</span> look like credentials or private keys
              (e.g. {sensitiveWarning?.samples.slice(0, 3).join(", ")}
              {(sensitiveWarning?.count ?? 0) > 3 ? ", …" : ""}). To avoid accidentally indexing secrets, they
              are skipped by default.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSensitiveWarning(null)}>Cancel</AlertDialogCancel>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setSensitiveWarning(null);
                runScan(false);
              }}
            >
              Continue anyway
            </Button>
            <AlertDialogAction
              onClick={() => {
                setSensitiveWarning(null);
                runScan(true);
              }}
            >
              Skip sensitive files
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ScanProgressDialog
        scanId={activeScanId}
        folderPath={folder.path}
        open={progressOpen}
        onOpenChange={setProgressOpen}
        onFinished={handleScanFinished}
      />
    </div>
  );
}
