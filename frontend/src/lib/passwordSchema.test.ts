import { describe, expect, it } from "vitest";
import { z } from "zod";

import { passwordSchema } from "@/lib/passwordSchema";

describe("passwordSchema", () => {
  it("rejects passwords shorter than 8 characters", () => {
    const result = passwordSchema.safeParse("Ab1!aB");
    expect(result.success).toBe(false);
  });

  it("rejects a password missing a lowercase letter", () => {
    const result = passwordSchema.safeParse("PASSWORD1!");
    expect(result.success).toBe(false);
  });

  it("rejects a password missing an uppercase letter", () => {
    const result = passwordSchema.safeParse("password1!");
    expect(result.success).toBe(false);
  });

  it("rejects a password missing a digit", () => {
    const result = passwordSchema.safeParse("Password!!");
    expect(result.success).toBe(false);
  });

  it("rejects a password missing a special character", () => {
    const result = passwordSchema.safeParse("Password123");
    expect(result.success).toBe(false);
  });

  it("accepts a fully compliant password", () => {
    const result = passwordSchema.safeParse("Password123!");
    expect(result.success).toBe(true);
  });
});

/**
 * `RegisterForm.tsx` and `ResetPasswordForm.tsx` each define a local zod
 * object schema composing `passwordSchema` with a `confirmPassword` field and
 * a `.refine` for the mismatch check. Those schemas aren't exported (they're
 * component-local consts), so this reconstructs the exact same composition
 * to test the custom `.refine` logic in isolation, without touching the
 * working component files to export something they have no other reason to
 * export.
 */
const confirmPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

describe("confirm-password refine logic (RegisterForm/ResetPasswordForm shape)", () => {
  it("fails validation when confirmPassword is empty", () => {
    const result = confirmPasswordSchema.safeParse({ password: "Password123!", confirmPassword: "" });
    expect(result.success).toBe(false);
  });

  it("fails with a confirmPassword-scoped error when the two passwords differ", () => {
    const result = confirmPasswordSchema.safeParse({
      password: "Password123!",
      confirmPassword: "Different123!",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path.join(".") === "confirmPassword");
      expect(issue?.message).toBe("Passwords do not match");
    }
  });

  it("succeeds when password and confirmPassword match and are compliant", () => {
    const result = confirmPasswordSchema.safeParse({
      password: "Password123!",
      confirmPassword: "Password123!",
    });
    expect(result.success).toBe(true);
  });

  it("fails on the underlying password rule even if confirmPassword matches it", () => {
    const result = confirmPasswordSchema.safeParse({ password: "weak", confirmPassword: "weak" });
    expect(result.success).toBe(false);
  });
});
