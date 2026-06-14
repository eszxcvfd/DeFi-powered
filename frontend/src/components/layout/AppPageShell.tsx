import type { ReactNode } from "react";

/** Full-width page background used across portal pages (matches browser session). */
export function AppPageShell({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <div
      className="min-h-[calc(100vh-4rem)] bg-slate-50/80"
      data-testid={testId}
    >
      {children}
    </div>
  );
}

export const PAGE_CONTENT_CLASS = "px-4 sm:px-6 lg:px-8 py-6 max-w-[1600px] mx-auto";