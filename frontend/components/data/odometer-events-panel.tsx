"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate, formatNumber } from "@/lib/format";
import { useCreateOdometerEvent, useOdometerEvents } from "@/lib/queries/odometerEvents";
import type { OdometerEventType } from "@/lib/types";

export function OdometerEventsPanel({ vehicleId }: { vehicleId: number | undefined }) {
  const { data: events } = useOdometerEvents(vehicleId);
  const createEvent = useCreateOdometerEvent(vehicleId);

  const [eventType, setEventType] = useState<OdometerEventType>("faulty_period");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [oldReading, setOldReading] = useState("");
  const [newReading, setNewReading] = useState("");
  const [notes, setNotes] = useState("");

  const needsReadings = eventType === "replaced" || eventType === "reset";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createEvent.mutate(
      {
        event_type: eventType,
        start_date: startDate,
        end_date: needsReadings ? undefined : endDate || undefined,
        old_reading_at_change: needsReadings ? oldReading : undefined,
        new_reading_at_change: needsReadings ? newReading : undefined,
        notes: notes || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Odometer event logged");
          setStartDate("");
          setEndDate("");
          setOldReading("");
          setNewReading("");
          setNotes("");
        },
        onError: () => toast.error("Couldn't log that event"),
      },
    );
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3 rounded-md border p-3">
        <div className="space-y-1.5">
          <Label>Event type</Label>
          <Select value={eventType} onValueChange={(v) => setEventType(v as OdometerEventType)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="faulty_period">Faulty period</SelectItem>
              <SelectItem value="replaced">Replaced</SelectItem>
              <SelectItem value="reset">Reset</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="event-start">{needsReadings ? "Date of change" : "Start date"}</Label>
            <Input
              id="event-start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          {!needsReadings && (
            <div className="space-y-1.5">
              <Label htmlFor="event-end">End date (blank = ongoing)</Label>
              <Input
                id="event-end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          )}
        </div>

        {needsReadings && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="old-reading">Old reading</Label>
              <Input
                id="old-reading"
                type="number"
                inputMode="decimal"
                value={oldReading}
                onChange={(e) => setOldReading(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-reading">New reading</Label>
              <Input
                id="new-reading"
                type="number"
                inputMode="decimal"
                value={newReading}
                onChange={(e) => setNewReading(e.target.value)}
                required
              />
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="event-notes">Notes</Label>
          <Input id="event-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <Button type="submit" disabled={createEvent.isPending}>
          {createEvent.isPending ? "Saving…" : "Log event"}
        </Button>
      </form>

      <div className="space-y-2">
        {events?.length === 0 && (
          <p className="text-sm text-muted-foreground">No odometer events logged.</p>
        )}
        {events?.map((event) => (
          <div key={event.id} className="rounded-md border p-3 text-sm">
            <p className="font-medium capitalize">{event.event_type.replaceAll("_", " ")}</p>
            <p className="text-muted-foreground">
              {formatDate(event.start_date)}
              {event.end_date ? ` – ${formatDate(event.end_date)}` : " – ongoing"}
            </p>
            {event.old_reading_at_change && (
              <p className="text-muted-foreground">
                {formatNumber(event.old_reading_at_change)} km →{" "}
                {formatNumber(event.new_reading_at_change)} km
              </p>
            )}
            {event.notes && <p className="mt-1">{event.notes}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
