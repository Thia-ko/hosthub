import { Badge } from "@/components/ui/badge";
import type { InstanceStatus } from "@/lib/types";

const STATUS_LABEL: Record<InstanceStatus, string> = {
  active: "Ativa",
  paused: "Pausada",
  archived: "Arquivada",
};

const STATUS_VARIANT: Record<InstanceStatus, "default" | "secondary" | "outline"> = {
  active: "default",
  paused: "secondary",
  archived: "outline",
};

export function StatusBadge({ status }: { status: InstanceStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
