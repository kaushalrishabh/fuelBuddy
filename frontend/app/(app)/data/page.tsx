"use client";

import { Download } from "lucide-react";
import { useState } from "react";

import { EntriesTable } from "@/components/data/entries-table";
import { ImportPanel } from "@/components/data/import-panel";
import { OdometerEventsPanel } from "@/components/data/odometer-events-panel";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadUrl } from "@/lib/api";
import { useDefaultVehicle } from "@/lib/queries/vehicles";

export default function DataPage() {
  const { vehicle, isLoading } = useDefaultVehicle();
  const [exportRange, setExportRange] = useState<{ date_from?: string; date_to?: string }>({});

  if (isLoading || !vehicle) {
    return <p className="p-4 text-sm text-muted-foreground">Loading…</p>;
  }

  const exportParams = new URLSearchParams();
  if (exportRange.date_from) exportParams.set("date_from", exportRange.date_from);
  if (exportRange.date_to) exportParams.set("date_to", exportRange.date_to);
  const exportQs = exportParams.toString();

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Import</CardTitle>
        </CardHeader>
        <CardContent>
          <ImportPanel vehicleId={vehicle.id} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Entries</CardTitle>
          <a
            href={downloadUrl(
              `/api/vehicles/${vehicle.id}/export.xlsx${exportQs ? `?${exportQs}` : ""}`,
            )}
            className={buttonVariants({ size: "sm", variant: "outline" })}
          >
            <Download className="mr-1 size-4" />
            Export
          </a>
        </CardHeader>
        <CardContent>
          <EntriesTable vehicleId={vehicle.id} onFiltersChange={setExportRange} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Odometer events</CardTitle>
        </CardHeader>
        <CardContent>
          <OdometerEventsPanel vehicleId={vehicle.id} />
        </CardContent>
      </Card>
    </div>
  );
}
