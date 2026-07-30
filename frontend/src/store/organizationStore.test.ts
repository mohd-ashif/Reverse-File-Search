import { beforeEach, describe, expect, it } from "vitest";

import { useOrganizationStore } from "@/store/organizationStore";

const initialState = useOrganizationStore.getState();

describe("organizationStore", () => {
  beforeEach(() => {
    useOrganizationStore.setState(initialState, true);
  });

  it("starts with a null organization", () => {
    expect(useOrganizationStore.getState().organization).toBeNull();
  });

  it("setOrganization stores the organization object", () => {
    useOrganizationStore.getState().setOrganization({ id: 1, name: "Acme", slug: "acme" });
    expect(useOrganizationStore.getState().organization).toEqual({ id: 1, name: "Acme", slug: "acme" });
  });

  it("setOrganization(null) clears it directly", () => {
    useOrganizationStore.getState().setOrganization({ id: 1, name: "Acme", slug: "acme" });
    useOrganizationStore.getState().setOrganization(null);
    expect(useOrganizationStore.getState().organization).toBeNull();
  });

  it("clear() resets the organization to null", () => {
    useOrganizationStore.getState().setOrganization({ id: 2, name: "Globex", slug: "globex" });
    useOrganizationStore.getState().clear();
    expect(useOrganizationStore.getState().organization).toBeNull();
  });
});
