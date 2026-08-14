"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Script from "next/script";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandLockup } from "@/components/brand-mark";
import { FormStatus } from "@/components/state";
import { apiFetch, errorMessage } from "@/lib/api-client";

interface MeResponse {
  role: "admin" | "client";
}

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

/** Only follow same-origin relative paths (`/foo`) from the `next` query param - never an
 * absolute/protocol-relative URL, which would make this an open redirect. */
function safeNextPath(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  return value;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNextPath(searchParams.get("next"));
  const expired = searchParams.get("expired") === "1";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const formData = new FormData(event.currentTarget);
      const turnstileToken = formData.get("cf-turnstile-response");
      const user = await apiFetch<MeResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, turnstile_token: turnstileToken || null }),
      });
      router.push(next ?? (user.role === "admin" ? "/admin" : "/app"));
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, "Nao foi possivel entrar."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/40 px-4">
      {TURNSTILE_SITE_KEY ? (
        <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer />
      ) : null}
      <BrandLockup size="lg" subtitle="Plataforma de agentes de IA" />
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Entrar na sua conta</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {expired ? (
            <FormStatus tone="error">Sua sessao expirou. Entre novamente para continuar.</FormStatus>
          ) : null}
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            {TURNSTILE_SITE_KEY ? <div className="cf-turnstile" data-sitekey={TURNSTILE_SITE_KEY} /> : null}
            {error ? <FormStatus tone="error">{error}</FormStatus> : null}
            <Button type="submit" disabled={loading} className="mt-2">
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginView() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
