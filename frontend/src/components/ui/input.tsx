import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary)]",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";