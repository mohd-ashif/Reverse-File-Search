import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, FileSearch, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FileDetailDialog } from "@/features/files/FileDetailDialog";
import { useDebounce } from "@/hooks/useDebounce";
import { useFiles } from "@/hooks/useFiles";
import { useFolders } from "@/hooks/useFolders";
import { FILE_STATUS_LABEL, FILE_STATUS_VARIANT, formatBytes, formatDate } from "@/lib/status";
import type { IndexedFile } from "@/types/file";

type SortKey = "filename" | "size_bytes" | "status" | "created_at";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 10;

function SortButton({
  label,
  sortKey,
  activeKey,
  dir,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
}) {
  const Icon = activeKey !== sortKey ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className="inline-flex items-center gap-1 font-medium hover:text-foreground"
    >
      {label}
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}

export function FilesPage() {
  const [folderId, setFolderId] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [selectedFile, setSelectedFile] = useState<IndexedFile | null>(null);

  const debouncedSearch = useDebounce(search, 300);
  const { data: folders } = useFolders();
  const parsedFolderId = folderId === "all" ? undefined : Number(folderId);
  const { data: files, isLoading, isError, error, refetch } = useFiles(parsedFolderId);

  const filteredAndSorted = useMemo(() => {
    const filtered = (files ?? []).filter((file) =>
      file.filename.toLowerCase().includes(debouncedSearch.trim().toLowerCase())
    );
    const sorted = [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const comparison = typeof aVal === "number" && typeof bVal === "number"
        ? aVal - bVal
        : String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? comparison : -comparison;
    });
    return sorted;
  }, [files, debouncedSearch, sortKey, sortDir]);

  const pageCount = Math.max(Math.ceil(filteredAndSorted.length / PAGE_SIZE), 1);
  const currentPage = Math.min(page, pageCount);
  const pageItems = filteredAndSorted.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Indexed files</h1>
        <p className="text-sm text-muted-foreground">Browse files extracted from your monitored folders.</p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-base">Files</CardTitle>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search by filename..."
                className="w-full pl-8 sm:w-64"
                aria-label="Search files by filename"
              />
            </div>
            <Select
              value={folderId}
              onValueChange={(value) => {
                setFolderId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-full sm:w-56" aria-label="Filter by folder">
                <SelectValue placeholder="All folders" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All folders</SelectItem>
                {(folders ?? []).map((folder) => (
                  <SelectItem key={folder.id} value={String(folder.id)}>
                    {folder.path}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : isError ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : filteredAndSorted.length === 0 ? (
            <EmptyState
              icon={FileSearch}
              title="No files found"
              description={
                (files ?? []).length === 0
                  ? "Scan a monitored folder to index files."
                  : "No files match your current search or filter."
              }
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <SortButton label="Filename" sortKey="filename" activeKey={sortKey} dir={sortDir} onSort={handleSort} />
                    </TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>
                      <SortButton label="Size" sortKey="size_bytes" activeKey={sortKey} dir={sortDir} onSort={handleSort} />
                    </TableHead>
                    <TableHead>
                      <SortButton label="Status" sortKey="status" activeKey={sortKey} dir={sortDir} onSort={handleSort} />
                    </TableHead>
                    <TableHead>
                      <SortButton label="Indexed" sortKey="created_at" activeKey={sortKey} dir={sortDir} onSort={handleSort} />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pageItems.map((file) => (
                    <TableRow
                      key={file.id}
                      tabIndex={0}
                      className="cursor-pointer"
                      onClick={() => setSelectedFile(file)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") setSelectedFile(file);
                      }}
                    >
                      <TableCell className="max-w-xs truncate font-medium" title={file.filename}>
                        {file.filename}
                      </TableCell>
                      <TableCell className="uppercase text-xs text-muted-foreground">{file.file_type}</TableCell>
                      <TableCell>{formatBytes(file.size_bytes)}</TableCell>
                      <TableCell>
                        <Badge variant={FILE_STATUS_VARIANT[file.status]}>{FILE_STATUS_LABEL[file.status]}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{formatDate(file.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination
                page={currentPage}
                pageCount={pageCount}
                onPageChange={setPage}
                totalItems={filteredAndSorted.length}
                pageSize={PAGE_SIZE}
              />
            </>
          )}
        </CardContent>
      </Card>

      <FileDetailDialog file={selectedFile} onOpenChange={(open) => !open && setSelectedFile(null)} />
    </div>
  );
}
