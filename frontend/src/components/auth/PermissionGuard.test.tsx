import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { PermissionGuard } from "@/components/auth/PermissionGuard";
import { usePermissionStore } from "@/store/permissionStore";

describe("PermissionGuard", () => {
  beforeEach(() => {
    usePermissionStore.setState({ permissions: [] });
  });

  it("renders children when the permission is present", () => {
    usePermissionStore.getState().setPermissions(["folder.create"]);
    render(
      <PermissionGuard permission="folder.create">
        <button>Add Folder</button>
      </PermissionGuard>
    );
    expect(screen.getByRole("button", { name: "Add Folder" })).toBeInTheDocument();
  });

  it("renders nothing by default when the permission is absent", () => {
    usePermissionStore.getState().setPermissions(["folder.read"]);
    render(
      <PermissionGuard permission="folder.create">
        <button>Add Folder</button>
      </PermissionGuard>
    );
    expect(screen.queryByRole("button", { name: "Add Folder" })).not.toBeInTheDocument();
  });

  it("renders the provided fallback when the permission is absent", () => {
    usePermissionStore.getState().setPermissions([]);
    render(
      <PermissionGuard permission="folder.delete" fallback={<span>No access</span>}>
        <button>Delete</button>
      </PermissionGuard>
    );
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByText("No access")).toBeInTheDocument();
  });
});
