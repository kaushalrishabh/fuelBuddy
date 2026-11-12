"use client";

import { useEntries } from "@/lib/queries/entries";

export function usePlaceSuggestions(vehicleId: number | undefined) {
  const { data } = useEntries(vehicleId, {
    page: 1,
    page_size: 200,
    entry_type: "refuel",
    sort_by: "date",
    sort_dir: "desc",
  });

  const locations = new Set<string>();
  const stations = new Set<string>();
  for (const entry of data?.items ?? []) {
    if (entry.location) locations.add(entry.location);
    if (entry.station_name) stations.add(entry.station_name);
  }

  return { locations: [...locations], stations: [...stations] };
}
