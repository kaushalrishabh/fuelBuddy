"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<User>("/api/auth/me"),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      api.post<User>("/api/auth/login", payload),
    onSuccess: (user) => {
      queryClient.setQueryData(["auth", "me"], user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/api/auth/logout"),
    onSuccess: () => {
      queryClient.clear();
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => api.post("/api/auth/forgot-password", { email }),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (payload: { token: string; new_password: string }) =>
      api.post("/api/auth/reset-password", payload),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      api.post("/api/auth/change-password", payload),
  });
}
