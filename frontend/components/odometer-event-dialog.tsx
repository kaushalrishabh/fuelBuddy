"use client";

import { useState } from "react";
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
  // Lazy-initialized from `prefill`; the caller remounts this component with
  // a key derived from prefill whenever a new warning's fix is clicked, so
  // these reset correctly without syncing via an effect.
  const [startDate, setStartDate] = useState(prefill?.start_date ?? "");
  const [oldReading, setOldReading] = useState(prefill?.old_reading_at_change ?? "");
  const [newReading, setNewReading] = useState(prefill?.new_reading_at_change ?? "");
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // This form renders in a Dialog portal. React bubbles a portaled
    // form's submit through the *React* component tree, not just the DOM
    // tree, so without this an ancestor <form> (e.g. the Home page's
    // RefuelForm, if this dialog is ever rendered inside one again) would
    // also submit. Belt-and-suspenders alongside keeping this dialog a
    // sibling of any such form, not a descendant.
    e.stopPropagation();
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
              <Label htmlFor="old-reading">Old meter&apos;s last reading</Label>
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
              <Label htmlFor="new-reading">New meter&apos;s reading now</Label>
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
