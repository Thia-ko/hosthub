import { cookies } from "next/headers";

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export interface MeResponse {
  id: string;
  email: string;
  role: "admin" | "client";
  full_name: string;
}

export async function getCurrentUser(): Promise<MeResponse | null> {
  const cookieStore = await cookies();
  try {
    const response = await fetch(`${INTERNAL_API_URL}/api/v1/auth/me`, {
      headers: { cookie: cookieStore.toString() },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as MeResponse;
  } catch {
    return null;
  }
}
