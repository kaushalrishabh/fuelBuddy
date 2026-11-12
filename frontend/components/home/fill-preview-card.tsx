"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { FillPreview } from "@/lib/types";

export function FillPreviewCard({ preview }: { preview: FillPreview | null | undefined }) {
  if (!preview || preview.distance_since_last_full_km === null) return null;

  return (
    <Card className="bg-muted/50">
      <CardContent className="grid grid-cols-3 gap-4 py-4 text-center text-sm">
        <div>
          <p className="text-xs text-muted-foreground">Distance</p>
          <p className="font-medium">{formatNumber(preview.distance_since_last_full_km)} km</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">km/L</p>
          <p className="font-medium">
            {preview.km_per_l !== null ? formatNumber(preview.km_per_l) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Rs/km</p>
          <p className="font-medium">
            {preview.rs_per_km !== null ? formatCurrency(preview.rs_per_km) : "—"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
