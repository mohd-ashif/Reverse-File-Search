import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { Eye, EyeOff, MailCheck } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useRegister } from "@/hooks/useAuth";
import { passwordSchema } from "@/lib/passwordSchema";
import { cn } from "@/lib/utils";

const registerSchema = z
  .object({
    firstName: z.string().trim().min(1, "First name is required"),
    lastName: z.string().trim().min(1, "Last name is required"),
    email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
    agreeToTerms: z.boolean().refine((val) => val === true, {
      message: "You must agree to the Terms to continue",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

const STRENGTH_RULES: RegExp[] = [/.{8,}/, /[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/];

function usePasswordStrength(password: string) {
  return useMemo(() => {
    const score = STRENGTH_RULES.reduce((count, rule) => count + (rule.test(password) ? 1 : 0), 0);
    if (!password) return { score: 0, label: "", color: "bg-muted" };
    if (score <= 2) return { score, label: "Weak", color: "bg-destructive" };
    if (score === 3) return { score, label: "Fair", color: "bg-orange-500" };
    if (score === 4) return { score, label: "Good", color: "bg-yellow-500" };
    return { score, label: "Strong", color: "bg-green-500" };
  }, [password]);
}

export function RegisterForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const registerMutation = useRegister();

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
      agreeToTerms: false,
    },
  });

  const passwordValue = form.watch("password");
  const strength = usePasswordStrength(passwordValue);

  const onSubmit = (values: RegisterFormValues) => {
    // Backend's /register endpoint only accepts email/password/full_name —
    // there's no separate first_name/last_name field on that payload, so we
    // concatenate them client-side into the single full_name string.
    const fullName = `${values.firstName} ${values.lastName}`.trim();

    registerMutation.mutate(
      { email: values.email, password: values.password, full_name: fullName },
      {
        onSuccess: () => {
          setSubmittedEmail(values.email);
        },
        onError: (error) => {
          if (error instanceof ApiError && error.fieldErrors.length > 0) {
            error.fieldErrors.forEach((fieldError) => {
              const field = fieldError.field as keyof RegisterFormValues;
              if (field === "email" || field === "password") {
                form.setError(field, { message: fieldError.message });
              }
            });
            return;
          }
          if (error instanceof ApiError && error.status === 409) {
            form.setError("email", { message: "An account with this email already exists" });
            return;
          }
          toast.error("Failed to create account", {
            description: error instanceof Error ? error.message : "Unknown error",
          });
        },
      }
    );
  };

  if (submittedEmail) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <MailCheck className="h-10 w-10 text-primary" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Check your email</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          We sent a verification link to <span className="font-medium text-foreground">{submittedEmail}</span>.
          Verify your account before signing in.
        </p>
        <Button asChild variant="outline" className="mt-2">
          <Link to="/login">Back to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="firstName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>First name</FormLabel>
                <FormControl>
                  <Input placeholder="Jane" autoComplete="given-name" autoFocus {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="lastName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Last name</FormLabel>
                <FormControl>
                  <Input placeholder="Doe" autoComplete="family-name" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    autoComplete="new-password"
                    className="pr-10"
                    {...field}
                  />
                </FormControl>
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {passwordValue ? (
                <div className="space-y-1">
                  <div className="flex h-1.5 gap-1">
                    {STRENGTH_RULES.map((_, index) => (
                      <div
                        key={index}
                        className={cn(
                          "flex-1 rounded-full bg-muted",
                          index < strength.score && strength.color
                        )}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">Password strength: {strength.label}</p>
                </div>
              ) : null}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm password</FormLabel>
              <FormControl>
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="agreeToTerms"
          render={({ field }) => (
            <FormItem>
              <label className="flex items-start gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(event) => field.onChange(event.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-input"
                />
                <span>I agree to the Terms of Service and Privacy Policy</span>
              </label>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? <Spinner className="mr-2" /> : null}
          Create account
        </Button>
      </form>
    </Form>
  );
}
