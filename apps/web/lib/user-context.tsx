"use client";

import { createContext, useContext, type ReactNode } from "react";

export interface CurrentUser {
  fullName: string;
  email: string;
  role: "admin" | "client";
}

const CurrentUserContext = createContext<CurrentUser | null>(null);

/** Shares the server-fetched current user (see getCurrentUser in lib/api-server.ts) with any
 * client component nested under AppShell, avoiding a redundant /auth/me round trip for pages
 * that just need the user's name (e.g. the dashboard's welcome greeting). */
export function CurrentUserProvider({ user, children }: { user: CurrentUser; children: ReactNode }) {
  return <CurrentUserContext.Provider value={user}>{children}</CurrentUserContext.Provider>;
}

export function useCurrentUser() {
  const ctx = useContext(CurrentUserContext);
  if (!ctx) throw new Error("useCurrentUser must be used within CurrentUserProvider");
  return ctx;
}
