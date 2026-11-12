"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { OdometerEvent, OdometerEventType } from "@/lib/types";

export function useOdometerEvents(vehicleId: number | undefined) {
  return useQuery<OdometerEvent[]>({
    queryKey: ["odometer-events", vehicleId],
    queryFn: () => api.get<OdometerEvent[]>(`/api/vehicles/${vehicleId}/odometer-events`),
    enabled: vehicleId !== undefined,
  });
}

export interface OdometerEventPayload {
  event_type: OdometerEventType;
  start_date: string;
  end_date?: string;
  old_reading_at_change?: string;
  new_reading_at_change?: string;
  notes?: string;
}

export function useCreateOdometerEvent(vehicleId: number | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OdometerEventPayload) =>
      api.post<OdometerEvent>(`/api/vehicles/${vehicleId}/odometer-events`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["odometer-events", vehicleId] });
    },
  });
}
