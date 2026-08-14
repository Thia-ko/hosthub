import type { Metadata } from "next";
import { cookies } from "next/headers";
import { InstanceDetailLayoutClient } from "./layout-client";

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://api:8000";

async function getInstanceName(instanceId: string): Promise<string | null> {
  try {
    const cookieStore = await cookies();
    const response = await fetch(`${INTERNAL_API_URL}/api/v1/instances/${instanceId}`, {
      headers: { cookie: cookieStore.toString() },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const data = await response.json();
    return typeof data?.name === "string" ? data.name : null;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}): Promise<Metadata> {
  const { instanceId } = await params;
  const name = await getInstanceName(instanceId);
  return { title: name ? `${name} | Hosthub` : "Instancia | Hosthub" };
}

export default async function InstanceDetailLayout({
  params,
  children,
}: {
  params: Promise<{ instanceId: string }>;
  children: React.ReactNode;
}) {
  const { instanceId } = await params;
  return <InstanceDetailLayoutClient instanceId={instanceId}>{children}</InstanceDetailLayoutClient>;
}
