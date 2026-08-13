"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api-client";

interface MeResponse {
  role: "admin" | "client";
}

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

export default function LoginPage() {
  const router = useRouter();
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
      router.push(user.role === "admin" ? "/admin" : "/app");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nao foi possivel entrar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      {TURNSTILE_SITE_KEY ? (
        <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer />
      ) : null}
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Entrar na Hosthub</CardTitle>
        </CardHeader>
        <CardContent>
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
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" disabled={loading} className="mt-2">
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
