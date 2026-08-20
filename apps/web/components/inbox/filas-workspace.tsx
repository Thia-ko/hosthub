"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AttendanceQueueManager } from "@/components/inbox/attendance-queue-manager";
import { QueuePanel } from "@/components/inbox/queue-panel";

/** Shared between the client (/app/filas) and admin (/admin/instances/[id]/filas) routes, same
 * pattern as <ConversationView> - a Kanban board of active handoffs plus, in a second tab, the
 * named-queue CRUD (routing hints/keywords/priority) that feeds it. */
export function FilasWorkspace({ instanceId, conversationsHref }: { instanceId: string; conversationsHref: string }) {
  return (
    <Tabs defaultValue="atendimento" className="flex flex-col gap-4">
      <TabsList>
        <TabsTrigger value="atendimento">Atendimento</TabsTrigger>
        <TabsTrigger value="configuracao">Configurar filas</TabsTrigger>
      </TabsList>
      <TabsContent value="atendimento">
        <QueuePanel instanceId={instanceId} conversationsHref={conversationsHref} />
      </TabsContent>
      <TabsContent value="configuracao">
        <AttendanceQueueManager instanceId={instanceId} />
      </TabsContent>
    </Tabs>
  );
}
