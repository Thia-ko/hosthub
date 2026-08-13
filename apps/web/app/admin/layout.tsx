import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/api-server";
import { ThemeToggle } from "@/components/theme-toggle";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.role !== "admin") redirect("/app");

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="flex items-center justify-between border-b bg-background px-6 py-3">
        <p className="text-sm text-muted-foreground">Painel administrativo - {user.full_name}</p>
        <ThemeToggle />
      </header>
      <main className="p-6">{children}</main>
    </div>
  );
}
