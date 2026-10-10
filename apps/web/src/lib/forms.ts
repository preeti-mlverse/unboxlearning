// Client-side form rules (Zod). They mirror the API's Pydantic rules so people see problems before submitting;
// the API still validates everything, and its field errors are shown the same way.
import { z } from "zod";

export const password = z.string().min(8, "At least 8 characters").max(128)
  .regex(/[A-Za-z]/, "Add a letter").regex(/\d/, "Add a number");

export const signupSchema = z.object({
  role: z.enum(["learner", "educator", "school", "ngo", "organization"]),
  name: z.string().trim().min(2, "Enter your name").max(120),
  email: z.email("Enter a valid email"),
  phone: z.string().trim().regex(/^$|^[6-9]\d{9}$/, "Enter a 10-digit mobile number").optional(),
  org: z.string().trim().max(160).optional(),
  language: z.string(),
  password,
  agree: z.literal(true, { error: "Please accept the Terms and Privacy policy" }),
});

export const loginSchema = z.object({
  identifier: z.string().trim().min(3, "Enter your email or mobile number"),
  password: z.string().min(1, "Enter your password"),
  remember: z.boolean(),
});

export function fieldErrors(result: { success: boolean; error?: z.ZodError }): Record<string, string> {
  if (result.success || !result.error) return {};
  const out: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = String(issue.path[0] ?? "form");
    out[key] ??= issue.message;
  }
  return out;
}

export function safeNext(next: string | null): string | null {
  // only same-app paths, never another site
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}
