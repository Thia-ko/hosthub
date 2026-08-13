import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { hexToOklch } from "@/lib/color";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Hosthub",
  description: "Plataforma de agentes de IA para atendimento",
};

interface ThemeSettings {
  light_primary_color: string;
  light_secondary_color: string;
  dark_primary_color: string;
  dark_secondary_color: string;
}

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://api:8000";

async function getThemeSettings(): Promise<ThemeSettings | null> {
  try {
    const response = await fetch(`${INTERNAL_API_URL}/api/v1/theme`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as ThemeSettings;
  } catch {
    return null;
  }
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const theme = await getThemeSettings();

  const themeCss = theme
    ? `:root { --primary: oklch(${hexToOklch(theme.light_primary_color)}); --secondary: oklch(${hexToOklch(theme.light_secondary_color)}); }
       .dark { --primary: oklch(${hexToOklch(theme.dark_primary_color)}); --secondary: oklch(${hexToOklch(theme.dark_secondary_color)}); }`
    : "";

  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>{themeCss ? <style dangerouslySetInnerHTML={{ __html: themeCss }} /> : null}</head>
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
