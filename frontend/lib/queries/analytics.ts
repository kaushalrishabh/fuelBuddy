"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CostEfficiency,
  DataQualityReport,
  KPIs,
  MileagePoint,
  MonthlyPoint,
  PriceTrend,
  RankedPlace,
  Records,
  RidingPattern,
  SeasonalityPoint,
} from "@/lib/types";

export interface DateRangeParams {
  range?: string;
  year?: number;
  date_from?: string;
  date_to?: string;
}

function toQueryString(params: DateRangeParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function useKpis(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<KPIs>({
    queryKey: ["analytics", "kpis", vehicleId, params],
    queryFn: () => api.get<KPIs>(`/api/vehicles/${vehicleId}/analytics/kpis${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function useMileageOverTime(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<MileagePoint[]>({
    queryKey: ["analytics", "mileage-over-time", vehicleId, params],
    queryFn: () =>
      api.get<MileagePoint[]>(
        `/api/vehicles/${vehicleId}/analytics/mileage-over-time${toQueryString(params)}`,
      ),
    enabled: vehicleId !== undefined,
  });
}

export function useMonthlyBreakdown(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<MonthlyPoint[]>({
    queryKey: ["analytics", "monthly", vehicleId, params],
    queryFn: () =>
      api.get<MonthlyPoint[]>(`/api/vehicles/${vehicleId}/analytics/monthly${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function usePriceTrend(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<PriceTrend>({
    queryKey: ["analytics", "price-trend", vehicleId, params],
    queryFn: () =>
      api.get<PriceTrend>(`/api/vehicles/${vehicleId}/analytics/price-trend${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function useCostEfficiency(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<CostEfficiency>({
    queryKey: ["analytics", "cost-efficiency", vehicleId, params],
    queryFn: () =>
      api.get<CostEfficiency>(
        `/api/vehicles/${vehicleId}/analytics/cost-efficiency${toQueryString(params)}`,
      ),
    enabled: vehicleId !== undefined,
  });
}

export function useLocationRanking(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<RankedPlace[]>({
    queryKey: ["analytics", "locations", vehicleId, params],
    queryFn: () =>
      api.get<RankedPlace[]>(`/api/vehicles/${vehicleId}/analytics/locations${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function useStationRanking(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<RankedPlace[]>({
    queryKey: ["analytics", "stations", vehicleId, params],
    queryFn: () =>
      api.get<RankedPlace[]>(`/api/vehicles/${vehicleId}/analytics/stations${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function useSeasonality(vehicleId: number | undefined) {
  return useQuery<SeasonalityPoint[]>({
    queryKey: ["analytics", "seasonality", vehicleId],
    queryFn: () => api.get<SeasonalityPoint[]>(`/api/vehicles/${vehicleId}/analytics/seasonality`),
    enabled: vehicleId !== undefined,
  });
}

export function useRidingPattern(vehicleId: number | undefined) {
  return useQuery<RidingPattern>({
    queryKey: ["analytics", "riding-pattern", vehicleId],
    queryFn: () => api.get<RidingPattern>(`/api/vehicles/${vehicleId}/analytics/riding-pattern`),
    enabled: vehicleId !== undefined,
  });
}

export function useRecords(vehicleId: number | undefined, params: DateRangeParams = {}) {
  return useQuery<Records>({
    queryKey: ["analytics", "records", vehicleId, params],
    queryFn: () =>
      api.get<Records>(`/api/vehicles/${vehicleId}/analytics/records${toQueryString(params)}`),
    enabled: vehicleId !== undefined,
  });
}

export function useDataQuality(vehicleId: number | undefined) {
  return useQuery<DataQualityReport>({
    queryKey: ["analytics", "data-quality", vehicleId],
    queryFn: () => api.get<DataQualityReport>(`/api/vehicles/${vehicleId}/analytics/data-quality`),
    enabled: vehicleId !== undefined,
  });
}
