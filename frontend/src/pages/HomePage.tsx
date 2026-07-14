import { Link } from "react-router-dom";
import { FileStack, FolderOpen, MessageSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { GettingStarted } from "@/features/onboarding/GettingStarted";
import { useFiles } from "@/hooks/useFiles";
import { useFolders } from "@/hooks/useFolders";
import { FILE_STATUS_LABEL } from "@/lib/status";
import type { FileIndexStatus } from "@/types/file";

const STATUS_ORDER: FileIndexStatus[] = ["pending", "extracted", "embedded", "failed"];

export function HomePage() {
  const folders = useFolders();
  const files = useFiles();

  const isLoading = folders.isLoading || files.isLoading;
  const isError = folders.isError || files.isError;

  const statusCounts = STATUS_ORDER.reduce<Record<FileIndexStatus, number>>((acc, status) => {
    acc[status] = (files.data ?? []).filter((file) => file.status === status).length;
    return acc;
  }, { pending: 0, extracted: 0, embedded: 0, failed: 0 });

  const hasNoFolders = !isLoading && (folders.data ?? []).length === 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground">A quick snapshot of what's monitored and indexed.</p>
      </div>

      <GettingStarted />

      {hasNoFolders ? null : <hr className="border-border" />}

      {isError ? (
        <ErrorState
          error={folders.error ?? files.error}
          onRetry={() => {
            void folders.refetch();
            void files.refetch();
          }}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Monitored folders</CardTitle>
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {isLoading ? <Skeleton className="h-8 w-16" /> : <p className="text-3xl font-bold">{folders.data?.length ?? 0}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Indexed files</CardTitle>
                <FileStack className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {isLoading ? <Skeleton className="h-8 w-16" /> : <p className="text-3xl font-bold">{files.data?.length ?? 0}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Failed files</CardTitle>
                <FileStack className="h-4 w-4 text-destructive" />
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (
                  <p className="text-3xl font-bold text-destructive">{statusCounts.failed}</p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Indexing status breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {STATUS_ORDER.map((status) => (
                    <div key={status} className="rounded-md border p-3 text-center">
                      <p className="text-2xl font-semibold">{statusCounts[status]}</p>
                      <p className="text-xs text-muted-foreground">{FILE_STATUS_LABEL[status]}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link to="/folders">
                <FolderOpen className="mr-2 h-4 w-4" />
                Manage folders
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/files">
                <FileStack className="mr-2 h-4 w-4" />
                Browse files
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/search">
                <MessageSquare className="mr-2 h-4 w-4" />
                Chat with your files
              </Link>
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
