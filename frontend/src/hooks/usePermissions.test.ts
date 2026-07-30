import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { usePermissions } from "@/hooks/usePermissions";
import { usePermissionStore } from "@/store/permissionStore";

describe("usePermissions", () => {
  beforeEach(() => {
    usePermissionStore.setState({ permissions: [] });
  });

  it("returns the current permission list from permissionStore", () => {
    usePermissionStore.getState().setPermissions(["folder.read", "file.download"]);
    const { result } = renderHook(() => usePermissions());
    expect(result.current).toEqual(["folder.read", "file.download"]);
  });

  it("reflects an empty permission set", () => {
    const { result } = renderHook(() => usePermissions());
    expect(result.current).toEqual([]);
  });
});
