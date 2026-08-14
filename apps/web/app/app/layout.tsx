import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/api-server";
import { AppShell } from "@/components/app-shell";
import { OwnInstanceProvider } from "@/lib/instance-context";
import { InstanceSwitcherSlot } from "@/components/instance-switcher-slot";

export default async function ClientLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.role !== "client") redirect("/admin");

  return (
    <OwnInstanceProvider>
      <AppShell
        section="app"
        user={{ fullName: user.full_name, email: user.email, role: user.role }}
        topBar={<InstanceSwitcherSlot />}
      >
        {children}
      </AppShell>
    </OwnInstanceProvider>
  );
}
