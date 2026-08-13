import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/api-server";

export default async function ClientLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.role !== "client") redirect("/admin");

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background px-6 py-3">
        <p className="text-sm text-muted-foreground">Ola, {user.full_name}</p>
      </header>
      <main className="p-6">{children}</main>
    </div>
  );
}
