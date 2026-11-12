"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { EntryWarnings } from "@/components/entry-warnings";
import { FillPreviewCard } from "@/components/home/fill-preview-card";
import { OdometerEventDialog } from "@/components/odometer-event-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { todayIso } from "@/lib/format";
import { usePlaceSuggestions } from "@/lib/hooks/use-place-suggestions";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { useCreateEntry, usePreviewEntry } from "@/lib/queries/entries";
import type { OdometerStatus, SuggestedFix } from "@/lib/types";

const schema = z
  .object({
    date: z.string().min(1, "Date is required"),
    odometer_km: z.string().min(1, "Odometer is required"),
    litres: z.string().min(1, "Litres is required"),
    amount_rs: z.string().optional(),
    price_per_litre: z.string().optional(),
    fill_type: z.enum(["full", "partial"]),
    location: z.string().optional(),
    station_name: z.string().optional(),
    notes: z.string().optional(),
  })
  .refine((data) => Boolean(data.amount_rs) || Boolean(data.price_per_litre), {
    message: "Enter an amount or a price per litre",
    path: ["amount_rs"],
  });

type Values = z.infer<typeof schema>;

export function RefuelForm({ vehicleId }: { vehicleId: number | undefined }) {
  const { locations, stations } = usePlaceSuggestions(vehicleId);
  const createEntry = useCreateEntry(vehicleId);
  const previewEntry = usePreviewEntry(vehicleId);

  const [lastEdited, setLastEdited] = useState<"amount" | "price" | null>(null);
  const [odometerStatus, setOdometerStatus] = useState<OdometerStatus>("ok");
  const [distanceOverride, setDistanceOverride] = useState("");
  const [showOverrideField, setShowOverrideField] = useState(false);
  const [odometerDialogOpen, setOdometerDialogOpen] = useState(false);
  const [odometerDialogPrefill, setOdometerDialogPrefill] = useState<Record<string, string> | null>(
    null,
  );

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { date: todayIso(), fill_type: "full" },
  });

  const [date, odometerKm, litres, amount, price, fillType] = watch([
    "date",
    "odometer_km",
    "litres",
    "amount_rs",
    "price_per_litre",
    "fill_type",
  ]);

  useEffect(() => {
    if (lastEdited === "amount" && litres && amount) {
      setValue("price_per_litre", (Number(amount) / Number(litres)).toFixed(2));
    }
  }, [lastEdited, litres, amount, setValue]);

  useEffect(() => {
    if (lastEdited === "price" && litres && price) {
      setValue("amount_rs", (Number(price) * Number(litres)).toFixed(2));
    }
  }, [lastEdited, litres, price, setValue]);

  const debouncedKey = useDebouncedValue(
    JSON.stringify([date, odometerKm, litres, amount, price, fillType, odometerStatus, distanceOverride]),
    500,
  );

  useEffect(() => {
    const [d, o, l, a, p, f, status, override] = JSON.parse(debouncedKey) as string[];
    if (!d || !o || !l || (!a && !p)) return;
    previewEntry.mutate({
      entry_type: "refuel",
      date: d,
      odometer_km: o,
      litres: l,
      amount_rs: a || undefined,
      price_per_litre: p || undefined,
      fill_type: f as "full" | "partial",
      odometer_status: status as OdometerStatus,
      distance_override_km: override || undefined,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedKey]);

  const handleFix = (action: SuggestedFix["action"], fix: SuggestedFix) => {
    if (action === "mark_faulty") {
      setOdometerStatus("faulty");
      toast.info("Marked faulty — excluded from mileage math until fixed");
    } else if (action === "set_distance_override") {
      setShowOverrideField(true);
    } else if (action === "log_odometer_event") {
      setOdometerDialogPrefill(fix.prefill ?? null);
      setOdometerDialogOpen(true);
    }
  };

  const onSubmit = (values: Values) => {
    createEntry.mutate(
      {
        entry_type: "refuel",
        date: values.date,
        odometer_km: values.odometer_km,
        litres: values.litres,
        amount_rs: values.amount_rs || undefined,
        price_per_litre: values.price_per_litre || undefined,
        fill_type: values.fill_type,
        location: values.location || undefined,
        station_name: values.station_name || undefined,
        notes: values.notes || undefined,
        odometer_status: odometerStatus,
        distance_override_km: distanceOverride || undefined,
      },
      {
        onSuccess: (response) => {
          toast.success("Refuel saved");
          if (response.warnings.length > 0) {
            toast.warning(`${response.warnings.length} warning(s) on this entry — check Data to fix`);
          }
          reset({ date: todayIso(), fill_type: "full" });
          setOdometerStatus("ok");
          setDistanceOverride("");
          setShowOverrideField(false);
          setLastEdited(null);
        },
        onError: () => toast.error("Couldn't save this entry"),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="date">Date</Label>
          <Input id="date" type="date" {...register("date")} />
          {errors.date && <p className="text-sm text-destructive">{errors.date.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="odometer_km">Odometer (km)</Label>
          <Input
            id="odometer_km"
            type="number"
            inputMode="decimal"
            step="0.1"
            {...register("odometer_km")}
          />
          {errors.odometer_km && (
            <p className="text-sm text-destructive">{errors.odometer_km.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="litres">Litres</Label>
          <Input id="litres" type="number" inputMode="decimal" step="0.01" {...register("litres")} />
          {errors.litres && <p className="text-sm text-destructive">{errors.litres.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label>Fill type</Label>
          <Select value={fillType} onValueChange={(value) => setValue("fill_type", value as "full" | "partial")}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="full">Full tank</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="amount_rs">Amount (₹)</Label>
          <Input
            id="amount_rs"
            type="number"
            inputMode="decimal"
            step="0.01"
            {...register("amount_rs", { onChange: () => setLastEdited("amount") })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="price_per_litre">Price/L (₹)</Label>
          <Input
            id="price_per_litre"
            type="number"
            inputMode="decimal"
            step="0.01"
            {...register("price_per_litre", { onChange: () => setLastEdited("price") })}
          />
        </div>
      </div>
      {errors.amount_rs && <p className="text-sm text-destructive">{errors.amount_rs.message}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="location">Location</Label>
          <Input id="location" list="location-suggestions" {...register("location")} />
          <datalist id="location-suggestions">
            {locations.map((loc) => (
              <option key={loc} value={loc} />
            ))}
          </datalist>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="station_name">Station (optional)</Label>
          <Input id="station_name" list="station-suggestions" {...register("station_name")} />
          <datalist id="station-suggestions">
            {stations.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="notes">Notes</Label>
        <Textarea id="notes" rows={2} {...register("notes")} />
      </div>

      {showOverrideField && (
        <div className="space-y-1.5">
          <Label htmlFor="distance_override">Actual distance for this fill (km)</Label>
          <Input
            id="distance_override"
            type="number"
            inputMode="decimal"
            step="0.1"
            value={distanceOverride}
            onChange={(e) => setDistanceOverride(e.target.value)}
          />
        </div>
      )}

      <EntryWarnings warnings={previewEntry.data?.warnings ?? []} onFix={handleFix} />
      <FillPreviewCard preview={previewEntry.data?.preview} />

      <Button type="submit" className="w-full" disabled={createEntry.isPending}>
        {createEntry.isPending ? "Saving…" : "Save refuel"}
      </Button>

      <OdometerEventDialog
        vehicleId={vehicleId}
        open={odometerDialogOpen}
        onOpenChange={setOdometerDialogOpen}
        prefill={odometerDialogPrefill}
        onLogged={() => previewEntry.reset()}
      />
    </form>
  );
}
