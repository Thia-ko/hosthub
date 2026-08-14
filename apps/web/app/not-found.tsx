import Link from "next/link";
import { Button } from "@/components/ui/button";
import { BrandLockup } from "@/components/brand-mark";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/40 px-4 text-center">
      <BrandLockup size="lg" subtitle="Plataforma de agentes de IA" />
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Pagina nao encontrada</h1>
        <p className="text-sm text-muted-foreground">O endereco que voce acessou nao existe ou foi movido.</p>
      </div>
      <Button asChild>
        <Link href="/">Voltar ao inicio</Link>
      </Button>
    </div>
  );
}
