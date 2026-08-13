import Link from "next/link";

export default function AdminHomePage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Painel administrativo</h1>
      <p className="text-sm text-muted-foreground">
        Gerencie instancias, clientes, templates e configuracoes da plataforma.
      </p>
      <div className="flex gap-4">
        <Link className="text-sm text-primary hover:underline" href="/admin/instances">
          Instancias
        </Link>
        <Link className="text-sm text-primary hover:underline" href="/admin/templates">
          Templates
        </Link>
        <Link className="text-sm text-primary hover:underline" href="/admin/theme">
          Tema
        </Link>
      </div>
    </div>
  );
}
