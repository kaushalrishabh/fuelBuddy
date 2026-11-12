"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCommitImport } from "@/lib/queries/imports";
import type { ParsedRow } from "@/lib/types";

/** Mirrors the backend's minimal required-field checks, so rows fixed
 * inline in the preview don't get silently skipped at commit for having
 * a stale `errors` list from the original parse. */
function revalidate(row: ParsedRow): string[] {
  const errors: string[] = [];
  if (!row.entry_type) errors.push("Unknown entry type");
  if (!row.date) errors.push("Date is required");
  if (!row.litres) errors.push("Litres is required");
  if (row.entry_type === "refuel") {
    if (!row.odometer_km) errors.push("Odometer is required for refuel entries");
    if (!row.amount_rs && !row.price_per_litre) {
      errors.push("Amount or price per litre is required");
    }
  }
  if (row.entry_type === "fuel_removed" && !row.notes) {
    errors.push("Notes are required for fuel_removed entries");
  }
  return errors;
}

export function ImportPreviewTable({
  vehicleId,
  initialRows,
  onCommitted,
}: {
  vehicleId: number | undefined;
  initialRows: ParsedRow[];
  onCommitted: () => void;
}) {
  const [rows, setRows] = useState(initialRows);
  const [includeDuplicates, setIncludeDuplicates] = useState(false);
  const commitImport = useCommitImport(vehicleId);

  const updateRow = (index: number, patch: Partial<ParsedRow>) => {
    setRows((prev) => {
      const next = [...prev];
      const merged = { ...next[index], ...patch };
      merged.errors = revalidate(merged);
      next[index] = merged;
      return next;
    });
  };

  const errorRows = rows.filter((r) => r.errors.length > 0);
  const warningRows = rows.filter((r) => r.errors.length === 0 && r.warnings.length > 0);
  const duplicateRows = rows.filter((r) => r.errors.length === 0 && r.is_duplicate);
  const validRows = rows.filter((r) => r.errors.length === 0 && !r.is_duplicate);
  const includedCount = validRows.length + (includeDuplicates ? duplicateRows.length : 0);

  const handleCommit = () => {
    commitImport.mutate(
      { rows, skip_duplicates: !includeDuplicates },
      {
        onSuccess: (result) => {
          toast.success(
            `Imported ${result.imported} · skipped ${result.skipped_duplicates} duplicate(s), ${result.skipped_errors} error row(s)`,
          );
          onCommitted();
        },
        onError: () => toast.error("Import failed"),
      },
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-sm">
        <Badge variant="secondary">{validRows.length} ready</Badge>
        {warningRows.length > 0 && <Badge variant="outline">{warningRows.length} warning(s)</Badge>}
        {errorRows.length > 0 && <Badge variant="destructive">{errorRows.length} error(s)</Badge>}
        {duplicateRows.length > 0 && (
          <Badge variant="outline">{duplicateRows.length} possible duplicate(s)</Badge>
        )}
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[640px] text-xs">
          <thead className="bg-muted text-left">
            <tr>
              <th className="p-2">Type</th>
              <th className="p-2">Date</th>
              <th className="p-2">Odometer</th>
              <th className="p-2">Litres</th>
              <th className="p-2">Amount</th>
              <th className="p-2">Notes</th>
              <th className="p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                key={row.row_number}
                className={
                  row.errors.length > 0
                    ? "bg-destructive/10"
                    : row.is_duplicate
                      ? "bg-muted"
                      : undefined
                }
              >
                <td className="p-2 align-top">{row.entry_type ?? "?"}</td>
                <td className="p-1 align-top">
                  <Input
                    className="h-7 w-32"
                    type="date"
                    value={row.date ?? ""}
                    onChange={(e) => updateRow(index, { date: e.target.value })}
                  />
                </td>
                <td className="p-1 align-top">
                  <Input
                    className="h-7 w-20"
                    value={row.odometer_km ?? ""}
                    onChange={(e) => updateRow(index, { odometer_km: e.target.value })}
                  />
                </td>
                <td className="p-1 align-top">
                  <Input
                    className="h-7 w-16"
                    value={row.litres ?? ""}
                    onChange={(e) => updateRow(index, { litres: e.target.value })}
                  />
                </td>
                <td className="p-1 align-top">
                  <Input
                    className="h-7 w-20"
                    value={row.amount_rs ?? ""}
                    onChange={(e) => updateRow(index, { amount_rs: e.target.value })}
                  />
                </td>
                <td className="p-1 align-top">
                  <Input
                    className="h-7 w-40"
                    value={row.notes}
                    onChange={(e) => updateRow(index, { notes: e.target.value })}
                  />
                </td>
                <td className="p-2 align-top">
                  {row.errors.length > 0 ? (
                    <span title={row.errors.join("; ")} className="text-destructive">
                      Error
                    </span>
                  ) : row.is_duplicate ? (
                    <span className="text-muted-foreground">Duplicate</span>
                  ) : row.warnings.length > 0 ? (
                    <span title={row.warnings.join("; ")} className="text-amber-600">
                      Warning
                    </span>
                  ) : (
                    <span className="text-emerald-600">OK</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {duplicateRows.length > 0 && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeDuplicates}
            onChange={(e) => setIncludeDuplicates(e.target.checked)}
          />
          Import possible duplicates anyway
        </label>
      )}

      <Button onClick={handleCommit} disabled={commitImport.isPending || includedCount === 0}>
        {commitImport.isPending ? "Importing…" : `Confirm import (${includedCount} rows)`}
      </Button>
    </div>
  );
}
