"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { useState } from "react";

import { EditEntryDialog } from "@/components/data/edit-entry-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import { useEntries } from "@/lib/queries/entries";
import type { Entry } from "@/lib/types";

const PAGE_SIZE = 25;

const SORTABLE_COLUMNS: { key: string; label: string }[] = [
  { key: "date", label: "Date" },
  { key: "odometer_km", label: "Odometer" },
  { key: "litres", label: "Litres" },
  { key: "amount_rs", label: "Amount" },
  { key: "price_per_litre", label: "Rs/L" },
];

export function EntryBadges({ entry }: { entry: Entry }) {
  return (
    <div className="flex flex-wrap gap-1">
      {entry.entry_type === "fuel_removed" && <Badge variant="secondary">Removed</Badge>}
      {entry.odometer_status === "faulty" && <Badge variant="destructive">Faulty</Badge>}
      {entry.odometer_status === "estimated" && <Badge variant="outline">Estimated</Badge>}
    </div>
  );
}

export function EntriesTable({
  vehicleId,
  onFiltersChange,
}: {
  vehicleId: number | undefined;
  onFiltersChange?: (filters: { date_from?: string; date_to?: string }) => void;
}) {
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [location, setLocation] = useState("");
  const [entryType, setEntryType] = useState("all");
  const [odometerStatus, setOdometerStatus] = useState("all");
  const [sortBy, setSortBy] = useState("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [editingEntry, setEditingEntry] = useState<Entry | null>(null);

  const filters = {
    page,
    page_size: PAGE_SIZE,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    location: location || undefined,
    entry_type: entryType === "all" ? undefined : entryType,
    odometer_status: odometerStatus === "all" ? undefined : odometerStatus,
    sort_by: sortBy,
    sort_dir: sortDir,
  };

  const { data, isLoading } = useEntries(vehicleId, filters);

  const toggleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  const applyDateFilter = () => {
    setPage(1);
    onFiltersChange?.({ date_from: dateFrom || undefined, date_to: dateTo || undefined });
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          onBlur={applyDateFilter}
          aria-label="From date"
        />
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          onBlur={applyDateFilter}
          aria-label="To date"
        />
        <Input
          placeholder="Location"
          value={location}
          onChange={(e) => {
            setLocation(e.target.value);
            setPage(1);
          }}
        />
        <Select
          value={entryType}
          onValueChange={(v) => {
            setEntryType(v ?? "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="refuel">Refuel</SelectItem>
            <SelectItem value="fuel_removed">Fuel removed</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={odometerStatus}
          onValueChange={(v) => {
            setOdometerStatus(v ?? "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All odometer statuses</SelectItem>
            <SelectItem value="ok">OK</SelectItem>
            <SelectItem value="faulty">Faulty</SelectItem>
            <SelectItem value="estimated">Estimated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {/* Desktop table */}
      <div className="hidden overflow-x-auto rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              {SORTABLE_COLUMNS.map((col) => (
                <TableHead key={col.key}>
                  <button
                    type="button"
                    className="flex items-center gap-1"
                    onClick={() => toggleSort(col.key)}
                  >
                    {col.label}
                    {sortBy === col.key &&
                      (sortDir === "asc" ? (
                        <ArrowUp className="size-3" />
                      ) : (
                        <ArrowDown className="size-3" />
                      ))}
                  </button>
                </TableHead>
              ))}
              <TableHead>Location</TableHead>
              <TableHead>Notes</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.items.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>
                  {formatDate(entry.date)}
                  <EntryBadges entry={entry} />
                </TableCell>
                <TableCell>{entry.odometer_km ? formatNumber(entry.odometer_km) : "—"}</TableCell>
                <TableCell>{formatNumber(entry.litres)}</TableCell>
                <TableCell>{formatCurrency(entry.amount_rs)}</TableCell>
                <TableCell>
                  {entry.price_per_litre ? formatCurrency(entry.price_per_litre) : "—"}
                </TableCell>
                <TableCell>{entry.location ?? "—"}</TableCell>
                <TableCell className="max-w-48 truncate">{entry.notes ?? "—"}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" onClick={() => setEditingEntry(entry)}>
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <div className="space-y-2 md:hidden">
        {data?.items.map((entry) => (
          <div key={entry.id} className="rounded-md border p-3 text-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{formatDate(entry.date)}</p>
                <EntryBadges entry={entry} />
              </div>
              <Button variant="ghost" size="sm" onClick={() => setEditingEntry(entry)}>
                Edit
              </Button>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1 text-muted-foreground">
              <span>Odometer: {entry.odometer_km ? formatNumber(entry.odometer_km) : "—"}</span>
              <span>Litres: {formatNumber(entry.litres)}</span>
              <span>Amount: {formatCurrency(entry.amount_rs)}</span>
              <span>Location: {entry.location ?? "—"}</span>
            </div>
            {entry.notes && <p className="mt-1 text-muted-foreground">{entry.notes}</p>}
          </div>
        ))}
      </div>

      {data && data.total === 0 && (
        <p className="py-6 text-center text-sm text-muted-foreground">No entries match these filters.</p>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Page {page} of {totalPages} ({data?.total ?? 0} entries)
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      <EditEntryDialog
        key={editingEntry?.id ?? "none"}
        vehicleId={vehicleId}
        entry={editingEntry}
        open={editingEntry !== null}
        onOpenChange={(open) => !open && setEditingEntry(null)}
      />
    </div>
  );
}
