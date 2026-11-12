"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Entry, EntryListResponse, EntryPreviewResponse, EntrySaveResponse } from "@/lib/types";

export interface EntryFilters {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  location?: string;
  entry_type?: string;
  odometer_status?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

function toQueryString(filters: EntryFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useEntries(vehicleId: number | undefined, filters: EntryFilters) {
  return useQuery<EntryListResponse>({
    queryKey: ["entries", vehicleId, filters],
    queryFn: () => api.get<EntryListResponse>(`/api/vehicles/${vehicleId}/entries${toQueryString(filters)}`),
    enabled: vehicleId !== undefined,
  });
}

// RefuelPayload/FuelRemovedPayload mirror the backend's discriminated EntryCreate union.
export interface RefuelPayload {
  entry_type: "refuel";
  date: string;
  odometer_km: string;
  litres: string;
  amount_rs?: string;
  price_per_litre?: string;
  fill_type?: "full" | "partial";
  location?: string;
  station_name?: string;
  notes?: string;
  odometer_status?: "ok" | "faulty" | "estimated";
  distance_override_km?: string;
}

export interface FuelRemovedPayload {
  entry_type: "fuel_removed";
  date: string;
  litres: string;
  odometer_km?: string;
  notes: string;
}

export type EntryPayload = RefuelPayload | FuelRemovedPayload;

export function useCreateEntry(vehicleId: number | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: EntryPayload) =>
      api.post<EntrySaveResponse>(`/api/vehicles/${vehicleId}/entries`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["entries", vehicleId] });
    },
  });
}

export function usePreviewEntry(vehicleId: number | undefined) {
  return useMutation({
    mutationFn: (payload: EntryPayload) =>
      api.post<EntryPreviewResponse>(`/api/vehicles/${vehicleId}/entries/preview`, payload),
  });
}

export function useUpdateEntry(vehicleId: number | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, payload }: { entryId: number; payload: Partial<Entry> }) =>
      api.patch<EntrySaveResponse>(`/api/vehicles/${vehicleId}/entries/${entryId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["entries", vehicleId] });
    },
  });
}
