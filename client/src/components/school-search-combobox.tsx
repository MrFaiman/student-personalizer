import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Loader2 } from "lucide-react";

import { searchSchools } from "@/lib/api/schools";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function useDebouncedValue<T>(value: T, ms: number): T {
  const [d, setD] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setD(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return d;
}

export type SchoolSelection =
  | { kind: "all" }
  | { kind: "none" }
  | { kind: "school"; id: number; name: string };

type MashovSchoolComboboxProps = {
  disabled?: boolean;
  selection: SchoolSelection;
  onSelectionChange: (s: SchoolSelection) => void;
  withAll: boolean;
  withNone: boolean;
  allLabel: string;
  noneLabel: string;
  searchPlaceholder?: string;
  className?: string;
};

export function MashovSchoolCombobox({
  disabled,
  selection,
  onSelectionChange,
  withAll,
  withNone,
  allLabel,
  noneLabel,
  searchPlaceholder = "חיפוש לפי שם או סמל…",
  className,
}: MashovSchoolComboboxProps) {
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const debounced = useDebouncedValue(searchInput, 280);
  const rootRef = useRef<HTMLDivElement>(null);

  const debouncedForQuery = open ? debounced : "";
  const { data: results = [], isFetching } = useQuery({
    queryKey: ["schools-search", debouncedForQuery],
    queryFn: () => searchSchools(debouncedForQuery, 50),
    staleTime: 5 * 60_000,
    enabled: open,
  });

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  useEffect(() => {
    if (open) setSearchInput("");
  }, [open]);

  const triggerLabel =
    selection.kind === "all"
      ? allLabel
      : selection.kind === "none"
        ? noneLabel
        : selection.name;

  return (
    <div ref={rootRef} className={cn("relative", className)} dir="rtl">
      <Button
        type="button"
        variant="outline"
        className="w-full justify-between gap-2 font-normal"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="min-w-0 truncate text-right">{triggerLabel}</span>
        <ChevronDown className="size-4 shrink-0 opacity-50" />
      </Button>
      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[280px] rounded-md border bg-popover p-2 shadow-md">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={searchPlaceholder}
            className="mb-2"
            autoFocus
          />
          <div className="max-h-60 overflow-y-auto space-y-0.5">
            {isFetching && (
              <div className="flex justify-center py-2 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
              </div>
            )}
            {!isFetching && withAll && (
              <button
                type="button"
                className="w-full rounded-sm px-2 py-1.5 text-right text-sm hover:bg-accent"
                onClick={() => {
                  onSelectionChange({ kind: "all" });
                  setOpen(false);
                }}
              >
                {allLabel}
              </button>
            )}
            {!isFetching && withNone && (
              <button
                type="button"
                className="w-full rounded-sm px-2 py-1.5 text-right text-sm hover:bg-accent"
                onClick={() => {
                  onSelectionChange({ kind: "none" });
                  setOpen(false);
                }}
              >
                {noneLabel}
              </button>
            )}
            {!isFetching &&
              results.map((s) => (
                <button
                  key={s.school_id}
                  type="button"
                  className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-right text-sm hover:bg-accent"
                  onClick={() => {
                    onSelectionChange({ kind: "school", id: s.school_id, name: s.school_name });
                    setOpen(false);
                  }}
                >
                  <span className="min-w-0 truncate">{s.school_name}</span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground tabular-nums">
                    {s.school_id}
                  </span>
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
