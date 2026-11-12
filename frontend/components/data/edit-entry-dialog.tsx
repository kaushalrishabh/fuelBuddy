"use client";

import { useState } from "react";
import { toast } from "sonner";

import { EntryWarnings } from "@/components/entry-warnings";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useUpdateEntry } from "@/lib/queries/entries";
import type { Entry, OdometerStatus } from "@/lib/types";

export function EditEntryDialog({
  vehicleId,
  entry,
  open,
  onOpenChange,
}: {
  vehicleId: number | undefined;
  entry: Entry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateEntry = useUpdateEntry(vehicleId);
  // Lazy-initialized from `entry`; the parent remounts this component with a
  // key={entry.id} whenever a different entry is opened, so these reset
  // correctly without syncing via an effect.
  const [fields, setFields] = useState<Record<string, string>>(() => ({
    date: entry?.date ?? "",
    odometer_km: entry?.odometer_km ?? "",
    litres: entry?.litres ?? "",
    amount_rs: entry?.amount_rs ?? "",
    price_per_litre: entry?.price_per_litre ?? "",
    location: entry?.location ?? "",
    station_name: entry?.station_name ?? "",
    notes: entry?.notes ?? "",
    distance_override_km: entry?.distance_override_km ?? "",
  }));
  const [odometerStatus, setOdometerStatus] = useState<OdometerStatus>(
    () => entry?.odometer_status ?? "ok",
  );

  if (!entry) return null;
  const isRefuel = entry.entry_type === "refuel";

  const set = (key: string, value: string) => setFields((prev) => ({ ...prev, [key]: value }));

  const handleSave = () => {
    updateEntry.mutate(
      {
        entryId: entry.id,
        payload: {
          date: fields.date,
          odometer_km: fields.odometer_km || undefined,
          litres: fields.litres,
          ...(isRefuel
            ? {
                amount_rs: fields.amount_rs || undefined,
                price_per_litre: fields.price_per_litre || undefined,
                location: fields.location || undefined,
                station_name: fields.station_name || undefined,
                distance_override_km: fields.distance_override_km || undefined,
              }
            : {}),
          notes: fields.notes || undefined,
          odometer_status: odometerStatus,
        } as Partial<Entry>,
      },
      {
        onSuccess: (response) => {
          toast.success("Entry updated");
          if (response.warnings.length === 0) {
            onOpenChange(false);
          }
        },
        onError: () => toast.error("Couldn't update this entry"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit {isRefuel ? "refuel" : "fuel removed"} entry</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Date</Label>
              <Input type="date" value={fields.date ?? ""} onChange={(e) => set("date", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Odometer (km)</Label>
              <Input
                type="number"
                inputMode="decimal"
                value={fields.odometer_km ?? ""}
                onChange={(e) => set("odometer_km", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Litres</Label>
              <Input
                type="number"
                inputMode="decimal"
                value={fields.litres ?? ""}
                onChange={(e) => set("litres", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Odometer status</Label>
              <Select value={odometerStatus} onValueChange={(v) => setOdometerStatus(v as OdometerStatus)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ok">OK</SelectItem>
                  <SelectItem value="faulty">Faulty</SelectItem>
                  <SelectItem value="estimated">Estimated</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {isRefuel && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    inputMode="decimal"
                    value={fields.amount_rs ?? ""}
                    onChange={(e) => set("amount_rs", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Price/L (₹)</Label>
                  <Input
                    type="number"
                    inputMode="decimal"
                    value={fields.price_per_litre ?? ""}
                    onChange={(e) => set("price_per_litre", e.target.value)}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Location</Label>
                  <Input value={fields.location ?? ""} onChange={(e) => set("location", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>Station</Label>
                  <Input
                    value={fields.station_name ?? ""}
                    onChange={(e) => set("station_name", e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Distance override (km)</Label>
                <Input
                  type="number"
                  inputMode="decimal"
                  value={fields.distance_override_km ?? ""}
                  onChange={(e) => set("distance_override_km", e.target.value)}
                />
              </div>
            </>
          )}

          <div className="space-y-1.5">
            <Label>Notes</Label>
            <Textarea rows={2} value={fields.notes ?? ""} onChange={(e) => set("notes", e.target.value)} />
          </div>

          <EntryWarnings
            warnings={updateEntry.data?.warnings ?? []}
            onFix={(action) => {
              if (action === "mark_faulty") setOdometerStatus("faulty");
            }}
          />
        </div>

        <DialogFooter>
          <Button onClick={handleSave} disabled={updateEntry.isPending}>
            {updateEntry.isPending ? "Saving…" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
