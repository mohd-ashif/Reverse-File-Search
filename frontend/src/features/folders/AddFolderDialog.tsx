import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { useCreateFolder, useEstimateFolder } from "@/hooks/useFolders";
import { ApiError } from "@/api/client";
import { classifyFolderRisk, FOLDER_TOO_BROAD_MESSAGE, isFolderPathTooBroad } from "@/lib/folderRisk";
import { RiskBadge } from "@/features/folders/RiskBadge";
import { FolderEstimatePreview } from "@/features/folders/FolderEstimatePreview";
import type { FolderEstimate } from "@/types/scan";

const folderFormSchema = z.object({
  path: z
    .string()
    .trim()
    .min(1, "Folder path is required")
    .refine((value) => !isFolderPathTooBroad(value), { message: FOLDER_TOO_BROAD_MESSAGE }),
});

type FolderFormValues = z.infer<typeof folderFormSchema>;

// Statuses the backend uses for folder path/access problems (invalid,
// missing, too broad, permission denied, locked, unreachable, duplicate) —
// all of these are shown inline under the path field rather than a toast.
const FOLDER_PATH_ERROR_STATUSES = new Set([400, 403, 404, 409, 423, 503]);

export function AddFolderDialog() {
  const [open, setOpen] = useState(false);
  const [estimate, setEstimate] = useState<FolderEstimate | null>(null);
  const estimateFolder = useEstimateFolder();
  const createFolder = useCreateFolder();

  const form = useForm<FolderFormValues>({
    resolver: zodResolver(folderFormSchema),
    defaultValues: { path: "" },
  });

  const pathValue = form.watch("path");
  const trimmedPath = pathValue.trim();
  const riskAssessment = trimmedPath.length > 0 ? classifyFolderRisk(trimmedPath) : null;

  const resetAll = () => {
    form.reset();
    setEstimate(null);
    estimateFolder.reset();
  };

  const onEstimate = (values: FolderFormValues) => {
    estimateFolder.mutate(values, {
      onSuccess: (result) => setEstimate(result),
      onError: (error) => {
        if (error instanceof ApiError && error.fieldErrors.length > 0) {
          error.fieldErrors.forEach((fieldError) => {
            form.setError("path", { message: fieldError.message });
          });
          return;
        }
        if (error instanceof ApiError && error.status !== null && FOLDER_PATH_ERROR_STATUSES.has(error.status)) {
          form.setError("path", { message: error.message });
          return;
        }
        toast.error("Failed to estimate folder", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
      },
    });
  };

  const onCancelEstimate = () => {
    setEstimate(null);
    estimateFolder.reset();
  };

  const onContinue = () => {
    if (!estimate) return;
    createFolder.mutate(
      { path: estimate.path },
      {
        onSuccess: (folder) => {
          toast.success("Folder added", { description: folder.path });
          setOpen(false);
          resetAll();
        },
        onError: (error) => {
          setEstimate(null);
          if (error instanceof ApiError && error.status !== null && FOLDER_PATH_ERROR_STATUSES.has(error.status)) {
            form.setError("path", { message: error.message });
            return;
          }
          toast.error("Failed to add folder", {
            description: error instanceof Error ? error.message : "Unknown error",
          });
        },
      }
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) resetAll();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add folder
        </Button>
      </DialogTrigger>
      <DialogContent>
        {estimate ? (
          <>
            <DialogHeader>
              <DialogTitle>Review scan estimate</DialogTitle>
              <DialogDescription className="break-all">{estimate.path}</DialogDescription>
            </DialogHeader>

            <div className="mt-4">
              <FolderEstimatePreview estimate={estimate} />
            </div>

            <DialogFooter className="mt-6">
              <Button type="button" variant="outline" onClick={onCancelEstimate} disabled={createFolder.isPending}>
                Cancel
              </Button>
              <Button type="button" onClick={onContinue} disabled={createFolder.isPending}>
                {createFolder.isPending ? <Spinner className="mr-2" /> : null}
                Continue
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={form.handleSubmit(onEstimate)}>
            <DialogHeader>
              <DialogTitle>Add a folder to monitor</DialogTitle>
              <DialogDescription>
                Provide an absolute path on the server's filesystem. Files inside it will become searchable
                after you run a scan.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-4 space-y-2">
              <Label htmlFor="path">
                Folder path <span className="text-destructive">*</span>
              </Label>
              <Input
                id="path"
                placeholder="C:\Users\me\Documents\reports"
                autoFocus
                aria-invalid={form.formState.errors.path ? true : undefined}
                {...form.register("path")}
              />
              {form.formState.errors.path ? (
                <p className="text-sm text-destructive">{form.formState.errors.path.message}</p>
              ) : null}
            </div>

            {riskAssessment ? (
              <div className="mt-3">
                <RiskBadge assessment={riskAssessment} />
              </div>
            ) : null}

            <DialogFooter className="mt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={estimateFolder.isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={estimateFolder.isPending || riskAssessment?.level === "high"}
              >
                {estimateFolder.isPending ? <Spinner className="mr-2" /> : null}
                Estimate scan
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
