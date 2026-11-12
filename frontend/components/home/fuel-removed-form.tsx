"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { todayIso } from "@/lib/format";
import { useCreateEntry } from "@/lib/queries/entries";

const schema = z.object({
  date: z.string().min(1, "Date is required"),
  litres: z.string().min(1, "Litres is required"),
  odometer_km: z.string().optional(),
  notes: z.string().min(1, "Notes are required — say what the fuel was used for"),
});

type Values = z.infer<typeof schema>;

export function FuelRemovedForm({ vehicleId }: { vehicleId: number | undefined }) {
  const createEntry = useCreateEntry(vehicleId);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { date: todayIso() } });

  const onSubmit = (values: Values) => {
    createEntry.mutate(
      {
        entry_type: "fuel_removed",
        date: values.date,
        litres: values.litres,
        odometer_km: values.odometer_km || undefined,
        notes: values.notes,
      },
      {
        onSuccess: () => {
          toast.success("Fuel removal logged");
          // Explicitly clear every field -- reset() only touches the ones
          // listed, leaving the rest at their just-submitted values.
          reset({ date: todayIso(), litres: "", odometer_km: "", notes: "" });
        },
        onError: () => toast.error("Couldn't save this entry"),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="removed-date">Date</Label>
          <Input id="removed-date" type="date" {...register("date")} />
          {errors.date && <p className="text-sm text-destructive">{errors.date.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="removed-litres">Litres removed</Label>
          <Input
            id="removed-litres"
            type="number"
            inputMode="decimal"
            step="0.01"
            {...register("litres")}
          />
          {errors.litres && <p className="text-sm text-destructive">{errors.litres.message}</p>}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="removed-odometer">Odometer (km, optional)</Label>
        <Input
          id="removed-odometer"
          type="number"
          inputMode="decimal"
          step="0.1"
          {...register("odometer_km")}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="removed-notes">What was it used for?</Label>
        <Textarea id="removed-notes" rows={2} {...register("notes")} />
        {errors.notes && <p className="text-sm text-destructive">{errors.notes.message}</p>}
      </div>

      <Button type="submit" className="w-full" disabled={createEntry.isPending}>
        {createEntry.isPending ? "Saving…" : "Log removal"}
      </Button>
    </form>
  );
}
