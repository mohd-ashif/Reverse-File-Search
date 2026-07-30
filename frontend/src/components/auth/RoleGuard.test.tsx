import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { RoleGuard } from "@/components/auth/RoleGuard";
import { useRoleStore } from "@/store/roleStore";

describe("RoleGuard", () => {
  beforeEach(() => {
    useRoleStore.setState({ roles: [] });
  });

  it("renders children when the user holds the named role", () => {
    useRoleStore.getState().setRoles(["Viewer"]);
    render(
      <RoleGuard role="Viewer">
        <span>Viewer content</span>
      </RoleGuard>
    );
    expect(screen.getByText("Viewer content")).toBeInTheDocument();
  });

  it("renders fallback when the user does not hold the named role", () => {
    useRoleStore.getState().setRoles(["Employee"]);
    render(
      <RoleGuard role="Organization Admin" fallback={<span>Denied</span>}>
        <span>Admin content</span>
      </RoleGuard>
    );
    expect(screen.queryByText("Admin content")).not.toBeInTheDocument();
    expect(screen.getByText("Denied")).toBeInTheDocument();
  });

  it("renders children when the user holds one of several assigned roles", () => {
    useRoleStore.getState().setRoles(["Employee", "Super Admin"]);
    render(
      <RoleGuard role="Super Admin">
        <span>Super admin content</span>
      </RoleGuard>
    );
    expect(screen.getByText("Super admin content")).toBeInTheDocument();
  });

  it("renders nothing (default fallback) for a role the user doesn't hold", () => {
    useRoleStore.getState().setRoles(["Viewer"]);
    const { container } = render(<RoleGuard role="Nonexistent Role">Anything</RoleGuard>);
    expect(container).toBeEmptyDOMElement();
  });
});
