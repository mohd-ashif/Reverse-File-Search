import { beforeEach, describe, expect, it } from "vitest";

import { usePermissionStore } from "@/store/permissionStore";

const initialState = usePermissionStore.getState();

describe("permissionStore", () => {
  beforeEach(() => {
    usePermissionStore.setState(initialState, true);
  });

  it("starts with an empty permission list", () => {
    expect(usePermissionStore.getState().permissions).toEqual([]);
  });

  it("setPermissions replaces the permission list", () => {
    usePermissionStore.getState().setPermissions(["folder.read", "file.read"]);
    expect(usePermissionStore.getState().permissions).toEqual(["folder.read", "file.read"]);
  });

  it("clear() resets the permission list to empty", () => {
    usePermissionStore.getState().setPermissions(["folder.read", "admin.users"]);
    usePermissionStore.getState().clear();
    expect(usePermissionStore.getState().permissions).toEqual([]);
  });
});
