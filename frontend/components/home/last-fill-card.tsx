"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import { useKpis } from "@/lib/queries/analytics";
import { useEntries } from "@/lib/queries/entries";

export function LastFillCard({ vehicleId }: { vehicleId: number | undefined }) {
  const kpis = useKpis(vehicleId);
  const lastEntries = useEntries(vehicleId, {
    page: 1,
    page_size: 1,
    entry_type: "refuel",
    sort_by: "date",
    sort_dir: "desc",
  });
  const lastFill = lastEntries.data?.items[0];

  if (!lastFill) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          No refuels logged yet. Add your first fill above.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Last fill</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <Stat label="Date" value={formatDate(lastFill.date)} />
        <Stat label="Litres" value={`${formatNumber(lastFill.litres)} L`} />
        <Stat label="Amount" value={formatCurrency(lastFill.amount_rs)} />
        <Stat
          label="Lifetime avg"
          value={kpis.data?.lifetime_km_per_l ? `${formatNumber(kpis.data.lifetime_km_per_l)} km/L` : "—"}
        />
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
