"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Vehicle } from "@/lib/types";

export function useVehicles() {
  return useQuery<Vehicle[]>({
    queryKey: ["vehicles"],
    queryFn: () => api.get<Vehicle[]>("/api/vehicles"),
  });
}

/** The single vehicle this app manages today; the backend supports more. */
export function useDefaultVehicle() {
  const query = useVehicles();
  const vehicle = query.data?.find((v) => v.is_default) ?? query.data?.[0] ?? null;
  return { ...query, vehicle };
}

export function useUpdateVehicle(vehicleId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Pick<Vehicle, "name" | "make" | "model" | "purchase_date" | "tank_capacity_l" | "initial_odometer_km">>) =>
      api.patch<Vehicle>(`/api/vehicles/${vehicleId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
  });
}
