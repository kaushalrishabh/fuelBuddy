"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateOdometerEvent } from "@/lib/queries/odometerEvents";

export function OdometerEventDialog({
  vehicleId,
  open,
  onOpenChange,
  prefill,
  onLogged,
}: {
  vehicleId: number | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  prefill: Record<string, string> | null;
  onLogged: () => void;
}) {
  const createEvent = useCreateOdometerEvent(vehicleId);
  const [startDate, setStartDate] = useState("");
  const [oldReading, setOldReading] = useState("");
  const [newReading, setNewReading] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (prefill) {
      setStartDate(prefill.start_date ?? "");
      setOldReading(prefill.old_reading_at_change ?? "");
      setNewReading(prefill.new_reading_at_change ?? "");
    }
  }, [prefill]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createEvent.mutate(
      {
        event_type: "replaced",
        start_date: startDate,
        old_reading_at_change: oldReading,
        new_reading_at_change: newReading,
        notes: notes || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Odometer replacement logged");
          onOpenChange(false);
          onLogged();
        },
        onError: () => toast.error("Couldn't log the odometer event"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Log odometer replacement</DialogTitle>
          <DialogDescription>
            Readings from this date onward will be offset so your mileage history stays
            continuous.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="event-start-date">Date of replacement</Label>
            <Input
              id="event-start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="old-reading">Old meter's last reading</Label>
              <Input
                id="old-reading"
                type="number"
                inputMode="decimal"
                step="0.1"
                value={oldReading}
                onChange={(e) => setOldReading(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-reading">New meter's reading now</Label>
              <Input
                id="new-reading"
                type="number"
                inputMode="decimal"
                step="0.1"
                value={newReading}
                onChange={(e) => setNewReading(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="event-notes">Notes (optional)</Label>
            <Input id="event-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createEvent.isPending}>
              {createEvent.isPending ? "Saving…" : "Log replacement"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
