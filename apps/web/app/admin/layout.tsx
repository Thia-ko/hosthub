import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/api-server";
import { AppShell } from "@/components/app-shell";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.role !== "admin") redirect("/app");

  return (
    <AppShell section="admin" user={{ fullName: user.full_name, email: user.email, role: user.role }}>
      {children}
    </AppShell>
  );
}
