import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LIST_PAGE_SIZE } from "@/constants/listPageSize";

export function paginateTotalPages(totalItems: number, pageSize = LIST_PAGE_SIZE): number {
  return Math.max(1, Math.ceil(totalItems / pageSize));
}

export function paginateSlice<T>(items: T[], page: number, pageSize = LIST_PAGE_SIZE): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

type ListPaginationProps = {
  page: number;
  totalItems: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  testId?: string;
  className?: string;
};

export function ListPagination({
  page,
  totalItems,
  pageSize = LIST_PAGE_SIZE,
  onPageChange,
  testId = "list-pagination",
  className = "",
}: ListPaginationProps) {
  const totalPages = paginateTotalPages(totalItems, pageSize);
  if (totalItems <= pageSize) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 mt-4 pt-3 text-xs ${className}`}
      data-testid={testId}
    >
      <span className="text-slate-500 font-mono">
        {start}–{end} of {totalItems}
      </span>
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="h-7 px-2.5 border border-slate-200 text-[11px]"
          data-testid={`${testId}-prev`}
        >
          <ChevronLeft className="size-3.5" />
          Prev
        </Button>
        <span className="px-2 font-mono text-slate-600" data-testid={`${testId}-label`}>
          {page} / {totalPages}
        </span>
        <Button
          type="button"
          variant="ghost"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="h-7 px-2.5 border border-slate-200 text-[11px]"
          data-testid={`${testId}-next`}
        >
          Next
          <ChevronRight className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}