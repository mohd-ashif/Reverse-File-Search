import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { ChatPage } from "@/pages/ChatPage";
import { FilesPage } from "@/pages/FilesPage";
import { FoldersPage } from "@/pages/FoldersPage";
import { HomePage } from "@/pages/HomePage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="folders" element={<FoldersPage />} />
          <Route path="search" element={<ChatPage />} />
          <Route path="files" element={<FilesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
