import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type AppPageHeaderProps = {
  backTo?: string;
  backLabel?: string;
  title: string;
  subtitle?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
};

export function AppPageHeader({
  backTo,
  backLabel = "Back",
  title,
  subtitle,
  meta,
  actions,
}: AppPageHeaderProps) {
  return (
    <div className="border-b border-slate-200 bg-white sticky top-0 z-20 px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-4 min-w-0">
        {backTo ? (
          <Link to={backTo} className="text-xs text-slate-500 shrink-0 hover:text-slate-800">
            ← {backLabel}
          </Link>
        ) : null}
        <div className="min-w-0">
          <h1 className="text-base font-bold text-slate-900 truncate">{title}</h1>
          {subtitle ? (
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{subtitle}</p>
          ) : null}
          {meta ? <div className="mt-1">{meta}</div> : null}
        </div>
      </div>
      {actions ? <div className="flex items-center gap-2 flex-wrap shrink-0">{actions}</div> : null}
    </div>
  );
}