import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Instance } from "@/lib/types";

export function InstanceSwitcher({
  instances,
  selectedId,
  onChange,
}: {
  instances: Instance[];
  selectedId: string;
  onChange: (id: string) => void;
}) {
  if (instances.length < 2) return null;

  return (
    <Select value={selectedId} onValueChange={onChange}>
      <SelectTrigger className="w-64">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {instances.map((instance) => (
          <SelectItem key={instance.id} value={instance.id}>
            {instance.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
