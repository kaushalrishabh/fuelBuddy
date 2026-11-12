"use client";

import { FuelRemovedForm } from "@/components/home/fuel-removed-form";
import { LastFillCard } from "@/components/home/last-fill-card";
import { RefuelForm } from "@/components/home/refuel-form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDefaultVehicle } from "@/lib/queries/vehicles";

export default function HomePage() {
  const { vehicle, isLoading } = useDefaultVehicle();

  if (isLoading) {
    return <p className="p-4 text-sm text-muted-foreground">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-md space-y-4 p-4">
      <Tabs defaultValue="refuel">
        <TabsList className="w-full">
          <TabsTrigger value="refuel" className="flex-1">
            Refuel
          </TabsTrigger>
          <TabsTrigger value="removed" className="flex-1">
            Fuel removed
          </TabsTrigger>
        </TabsList>
        <TabsContent value="refuel" className="mt-4">
          <RefuelForm vehicleId={vehicle?.id} />
        </TabsContent>
        <TabsContent value="removed" className="mt-4">
          <FuelRemovedForm vehicleId={vehicle?.id} />
        </TabsContent>
      </Tabs>

      <LastFillCard vehicleId={vehicle?.id} />
    </div>
  );
}
