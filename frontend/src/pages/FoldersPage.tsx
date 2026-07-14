import { FolderOpen } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AddFolderDialog } from "@/features/folders/AddFolderDialog";
import { FolderRowActions } from "@/features/folders/FolderRowActions";
import { useFolders } from "@/hooks/useFolders";
import { formatDate } from "@/lib/status";

export function FoldersPage() {
  const { data: folders, isLoading, isError, error, refetch } = useFolders();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Monitored folders</h1>
          <p className="text-sm text-muted-foreground">
            Add folders to watch, then scan them to extract and index their files for search.
          </p>
        </div>
        <AddFolderDialog />
      </div>

      <Card>
        <CardHeader className="pb-0">
          <CardTitle className="text-base">Folders</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : isError ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : folders && folders.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Path</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Added</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {folders.map((folder) => (
                  <TableRow key={folder.id}>
                    <TableCell className="max-w-md truncate font-mono text-xs" title={folder.path}>
                      {folder.path}
                    </TableCell>
                    <TableCell>
                      <Badge variant={folder.is_active ? "success" : "secondary"}>
                        {folder.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(folder.created_at)}
                    </TableCell>
                    <TableCell>
                      <FolderRowActions folder={folder} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              icon={FolderOpen}
              title="No folders monitored yet"
              description="Add your first folder to start indexing files for search."
              action={<AddFolderDialog />}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
