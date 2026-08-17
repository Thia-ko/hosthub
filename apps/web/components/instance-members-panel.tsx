"use client";

import { useState } from "react";
import { copyToClipboard } from "@/lib/utils";
import { Plus, Trash2, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { InstanceMember, InstanceMembersResponse } from "@/lib/types";

function MemberRow({
  member,
  canManage,
  onRemove,
}: {
  member: InstanceMember;
  canManage: boolean;
  onRemove: (userId: string) => Promise<void>;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate font-medium">{member.full_name}</span>
        <span className="truncate text-xs text-muted-foreground">{member.email}</span>
      </div>
      <Badge variant={member.role === "owner" ? "default" : "secondary"} className="shrink-0">
        {member.role === "owner" ? "Dono" : "Membro"}
      </Badge>
      {canManage ? (
        <ConfirmDialog
          trigger={
            <Button size="icon" variant="ghost" className="size-7 shrink-0">
              <Trash2 className="size-3.5" />
            </Button>
          }
          title="Remover da equipe"
          description={`Remover ${member.full_name} do acesso a esta instancia?`}
          confirmLabel="Remover"
          destructive
          onConfirm={() => onRemove(member.user_id)}
        />
      ) : null}
    </div>
  );
}

function InviteMemberForm({
  onInvite,
}: {
  onInvite: (email: string, fullName: string) => Promise<{ email: string; password: string } | null>;
}) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ email: string; password: string } | null>(null);

  async function submit() {
    if (!email.trim() || !fullName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const generated = await onInvite(email.trim(), fullName.trim());
      setEmail("");
      setFullName("");
      if (generated) {
        setCreated(generated);
      } else {
        setOpen(false);
      }
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  if (created) {
    return (
      <div className="flex flex-col gap-2 rounded-md border bg-muted/40 p-3 text-sm">
        <p className="text-muted-foreground">
          Compartilhe estas credenciais com a pessoa convidada. A senha nao sera exibida novamente.
        </p>
        <span>
          <strong>E-mail:</strong> {created.email}
        </span>
        <span>
          <strong>Senha:</strong> {created.password}
        </span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => copyToClipboard(created.password)}>
            Copiar senha
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setCreated(null);
              setOpen(false);
            }}
          >
            Fechar
          </Button>
        </div>
      </div>
    );
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="w-fit" onClick={() => setOpen(true)}>
        <Plus className="size-3.5" /> Convidar membro
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed p-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="memberEmail">E-mail</Label>
        <Input id="memberEmail" value={email} onChange={(event) => setEmail(event.target.value)} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="memberFullName">Nome completo</Label>
        <Input id="memberFullName" value={fullName} onChange={(event) => setFullName(event.target.value)} />
      </div>
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !email.trim() || !fullName.trim()}>
          Convidar
        </Button>
        <Button size="sm" variant="outline" onClick={() => setOpen(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

export function InstanceMembersPanel({ instanceId }: { instanceId: string }) {
  const {
    data,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<InstanceMembersResponse>(`/instances/${instanceId}/members`), [instanceId]);

  async function invite(email: string, fullName: string) {
    const result = await apiFetch<{ member: InstanceMember; generated_password: string | null }>(
      `/instances/${instanceId}/members`,
      { method: "POST", body: JSON.stringify({ email, full_name: fullName }) }
    );
    reload();
    return result.generated_password ? { email: result.member.email, password: result.generated_password } : null;
  }

  async function remove(userId: string) {
    await apiFetch(`/instances/${instanceId}/members/${userId}`, { method: "DELETE" });
    reload();
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">Equipe</p>
        <p className="text-xs text-muted-foreground">
          Pessoas com acesso a esta instancia - veem e editam o prompt, conversas e dados coletados como o
          dono.
        </p>
      </div>
      {loading && !data ? <LoadingState /> : null}
      {!data && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {data && data.members.length === 0 ? <EmptyState title="Nenhum membro ainda." icon={Users} /> : null}
      {data && data.members.length > 0 ? (
        <div className="flex flex-col gap-2">
          {data.members.map((member) => (
            <MemberRow key={member.id} member={member} canManage={data.can_manage} onRemove={remove} />
          ))}
        </div>
      ) : null}
      {data?.can_manage ? <InviteMemberForm onInvite={invite} /> : null}
    </div>
  );
}
