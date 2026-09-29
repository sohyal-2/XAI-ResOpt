"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { ArrowRight, KeyRound } from "lucide-react";

interface AuthFormProps {
  mode: "login" | "register";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const { login, signup, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setValidationError(null);
    if (!email.includes("@")) return setValidationError("Enter a valid email address.");
    if (password.length < 12) return setValidationError("Password must be at least 12 characters.");
    if (mode === "register" && !fullName.trim()) return setValidationError("Enter your full name.");
    if (mode === "register" && password !== confirmPassword) return setValidationError("Passwords do not match.");
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, fullName, password);
      }
      router.replace("/dashboard");
    } catch {
      // The provider exposes the API error in the form's alert.
    }
  }

  function fillDemo() {
    setEmail("alice.architect@example.com");
    setPassword("SecurePassword123!");
    if (mode === "register") {
      setFullName("Alice Architect");
      setConfirmPassword("SecurePassword123!");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#fcfbf7] px-4 sm:px-6 py-8 sm:py-12">
      <section className="w-full max-w-md border border-[#e6e2d8] bg-[#ffffff] p-6 sm:p-8 shadow-editorial">
        <div className="flex items-center justify-between border-b border-[#edeae1] pb-4">
          <Link className="flex items-center gap-2 min-h-[44px] sm:min-h-0" href="/">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[10px] font-bold text-[#fcfbf7]">
              X
            </span>
            <span className="font-mono text-xs font-semibold tracking-wider uppercase text-[#181816]">
              XAI-ResOpt
            </span>
          </Link>
          <span className="text-[11px] font-mono text-[#5c5953] uppercase font-bold">Secure Session</span>
        </div>

        <h1 className="mt-6 font-serif text-2xl font-normal tracking-tight text-[#181816]">
          {mode === "login" ? "Sign in to workspace" : "Create your account"}
        </h1>
        <p className="mt-1 text-xs text-[#5c5953]">
          {mode === "login"
            ? "Enter your credentials to access your analyses."
            : "Set up a private, evidence-grounded resume workspace."}
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
          {mode === "register" && (
            <div>
              <label htmlFor="auth-full-name" className="block text-xs font-medium text-[#181816]">
                Full Name
              </label>
              <input
                id="auth-full-name"
                className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none transition-colors min-h-[44px]"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="e.g. Alice Architect"
                autoComplete="name"
                required
              />
            </div>
          )}

          <div>
            <label htmlFor="auth-email" className="block text-xs font-medium text-[#181816]">
              Email Address
            </label>
            <input
              id="auth-email"
              className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none transition-colors min-h-[44px]"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@company.com"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label htmlFor="auth-password" className="block text-xs font-medium text-[#181816]">
              Password
            </label>
            <input
              id="auth-password"
              className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none transition-colors min-h-[44px]"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 12 characters"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </div>

          {mode === "register" && (
            <div>
              <label htmlFor="auth-confirm-password" className="block text-xs font-medium text-[#181816]">
                Confirm Password
              </label>
              <input
                id="auth-confirm-password"
                className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none transition-colors min-h-[44px]"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Confirm password"
                autoComplete="new-password"
                required
              />
            </div>
          )}

          {(validationError || error) && (
            <div className="rounded border border-[#f7d0ca] bg-[#fdf2f0] p-3 text-xs text-[#942e23]" role="alert">
              {validationError || error}
            </div>
          )}

          <button
            className="flex w-full items-center justify-center gap-2 rounded bg-[#181816] px-4 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-50 transition-colors shadow-sm min-h-[44px]"
            disabled={isLoading}
            type="submit"
          >
            {isLoading ? "Authenticating..." : mode === "login" ? "Sign In" : "Create Account"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[#edeae1] pt-4 text-xs">
          <p className="text-[#5c5953]">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <Link className="font-semibold text-[#181816] underline underline-offset-2 min-h-[44px] inline-flex items-center" href={mode === "login" ? "/register" : "/login"}>
              {mode === "login" ? "Create one" : "Sign in"}
            </Link>
          </p>
          <button
            onClick={fillDemo}
            type="button"
            className="flex items-center gap-1 font-mono text-[11px] text-[#5c5953] hover:text-[#181816] underline min-h-[44px]"
          >
            <KeyRound className="h-3 w-3" />
            Demo Fill
          </button>
        </div>
      </section>
    </main>
  );
}