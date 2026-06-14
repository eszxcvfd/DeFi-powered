import type { ReactNode } from "react";

type AppSectionProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  testId?: string;
  className?: string;
};

export function AppSection({
  title,
  description,
  actions,
  children,
  testId,
  className = "",
}: AppSectionProps) {
  return (
    <section
      className={`border border-slate-200 rounded-lg bg-white overflow-hidden shadow-sm ${className}`}
      data-testid={testId}
    >
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/80 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600">{title}</h2>
          {description ? (
            <p className="text-[11px] text-slate-500 mt-1 max-w-2xl">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2 shrink-0">{actions}</div> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}