"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ImportCommitResponse, ImportPreviewResponse, ParsedRow } from "@/lib/types";

export function usePreviewRawText(vehicleId: number | undefined) {
  return useMutation({
    mutationFn: (payload: { text: string; start_year: number }) =>
      api.post<ImportPreviewResponse>(`/api/vehicles/${vehicleId}/import/raw-text/preview`, payload),
  });
}

export function usePreviewExcel(vehicleId: number | undefined) {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.postForm<ImportPreviewResponse>(
        `/api/vehicles/${vehicleId}/import/excel/preview`,
        form,
      );
    },
  });
}

export function useCommitImport(vehicleId: number | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { rows: ParsedRow[]; skip_duplicates?: boolean }) =>
      api.post<ImportCommitResponse>(`/api/vehicles/${vehicleId}/import/commit`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["entries", vehicleId] });
    },
  });
}
