import type { Metadata } from "next";
import LoginView from "./view";

export const metadata: Metadata = { title: "Entrar | Hosthub" };

export default function LoginPage() {
  return <LoginView />;
}
