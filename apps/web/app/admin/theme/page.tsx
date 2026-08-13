"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { apiFetch, ApiError } from "@/lib/api-client";
import { hexToOklch } from "@/lib/color";
import type { ThemeSettings } from "@/lib/types";

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-9 w-14 cursor-pointer rounded-md border"
        />
        <span className="text-sm text-muted-foreground">{value}</span>
      </div>
    </div>
  );
}

export default function AdminThemePage() {
  const { resolvedTheme } = useTheme();
  const [colors, setColors] = useState<ThemeSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ThemeSettings>("/theme").then(setColors);
  }, []);

  useEffect(() => {
    if (!colors) return;
    const primary = resolvedTheme === "dark" ? colors.dark_primary_color : colors.light_primary_color;
    const secondary = resolvedTheme === "dark" ? colors.dark_secondary_color : colors.light_secondary_color;
    document.documentElement.style.setProperty("--primary", `oklch(${hexToOklch(primary)})`);
    document.documentElement.style.setProperty("--secondary", `oklch(${hexToOklch(secondary)})`);
  }, [colors, resolvedTheme]);

  async function handleSave() {
    if (!colors) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await apiFetch<ThemeSettings>("/theme", {
        method: "PUT",
        body: JSON.stringify(colors),
      });
      setColors(updated);
      setMessage("Tema salvo. As novas cores valem para toda a plataforma.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Nao foi possivel salvar");
    } finally {
      setSaving(false);
    }
  }

  if (!colors) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <h1 className="text-xl font-semibold">Tema da plataforma</h1>
      <p className="text-sm text-muted-foreground">
        As cores abaixo valem para toda a plataforma (admin e clientes), tanto no modo claro quanto no escuro.
      </p>

      <div className="grid grid-cols-2 gap-4">
        <ColorField
          label="Primaria (claro)"
          value={colors.light_primary_color}
          onChange={(value) => setColors({ ...colors, light_primary_color: value })}
        />
        <ColorField
          label="Secundaria (claro)"
          value={colors.light_secondary_color}
          onChange={(value) => setColors({ ...colors, light_secondary_color: value })}
        />
        <ColorField
          label="Primaria (escuro)"
          value={colors.dark_primary_color}
          onChange={(value) => setColors({ ...colors, dark_primary_color: value })}
        />
        <ColorField
          label="Secundaria (escuro)"
          value={colors.dark_secondary_color}
          onChange={(value) => setColors({ ...colors, dark_secondary_color: value })}
        />
      </div>

      <div className="flex gap-2">
        <Button>Botao primario (preview)</Button>
        <Button variant="secondary">Botao secundario (preview)</Button>
      </div>

      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      <Button onClick={handleSave} disabled={saving} className="w-fit">
        {saving ? "Salvando..." : "Salvar tema"}
      </Button>
    </div>
  );
}
