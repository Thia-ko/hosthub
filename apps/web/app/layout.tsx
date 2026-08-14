import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { hexToOklch } from "@/lib/color";
import { getThemeSettings } from "@/lib/theme-settings";

const inter = Inter({
  variable: "--font-inter",
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

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const theme = await getThemeSettings();

  const themeCss = theme
    ? `:root { --primary: oklch(${hexToOklch(theme.light_primary_color)}); --secondary: oklch(${hexToOklch(theme.light_secondary_color)}); }
       .dark { --primary: oklch(${hexToOklch(theme.dark_primary_color)}); --secondary: oklch(${hexToOklch(theme.dark_secondary_color)}); }`
    : "";

  return (
    <html
      lang="pt-BR"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>{themeCss ? <style dangerouslySetInnerHTML={{ __html: themeCss }} /> : null}</head>
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
