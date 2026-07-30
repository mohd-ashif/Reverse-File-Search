import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuthStore } from "@/store/authStore";

function renderProtectedRoute(initialPath = "/dashboard") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, status: "idle" });
  });

  it("renders a full-page spinner while status is idle", () => {
    useAuthStore.getState().setStatus("idle");
    const { container } = renderProtectedRoute();
    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard content")).not.toBeInTheDocument();
  });

  it("renders a full-page spinner while status is loading", () => {
    useAuthStore.getState().setStatus("loading");
    const { container } = renderProtectedRoute();
    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard content")).not.toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated", () => {
    useAuthStore.getState().setStatus("unauthenticated");
    renderProtectedRoute();
    expect(screen.getByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard content")).not.toBeInTheDocument();
  });

  it("renders the nested route's content when authenticated", () => {
    useAuthStore.getState().setStatus("authenticated");
    renderProtectedRoute();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });
});
