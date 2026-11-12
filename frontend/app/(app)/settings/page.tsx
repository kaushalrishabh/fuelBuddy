"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useChangePassword } from "@/lib/queries/auth";
import { useDefaultVehicle, useUpdateVehicle } from "@/lib/queries/vehicles";

const vehicleSchema = z.object({
  name: z.string().min(1, "Name is required"),
  make: z.string().optional(),
  model: z.string().optional(),
  tank_capacity_l: z.string().min(1, "Tank capacity is required"),
  initial_odometer_km: z.string().optional(),
});

type VehicleValues = z.infer<typeof vehicleSchema>;

function VehicleSettingsCard() {
  const { vehicle, isLoading } = useDefaultVehicle();
  const updateVehicle = useUpdateVehicle(vehicle?.id ?? 0);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<VehicleValues>({ resolver: zodResolver(vehicleSchema) });

  useEffect(() => {
    if (vehicle) {
      reset({
        name: vehicle.name,
        make: vehicle.make ?? "",
        model: vehicle.model ?? "",
        tank_capacity_l: vehicle.tank_capacity_l,
        initial_odometer_km: vehicle.initial_odometer_km,
      });
    }
  }, [vehicle, reset]);

  if (isLoading || !vehicle) {
    return null;
  }

  const onSubmit = (values: VehicleValues) => {
    updateVehicle.mutate(values, {
      onSuccess: () => toast.success("Vehicle details saved"),
      onError: () => toast.error("Couldn't save vehicle details"),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Vehicle</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="make">Make</Label>
              <Input id="make" {...register("make")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="model">Model</Label>
              <Input id="model" {...register("model")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="tank_capacity_l">Tank capacity (L)</Label>
              <Input id="tank_capacity_l" type="number" inputMode="decimal" step="0.1" {...register("tank_capacity_l")} />
              {errors.tank_capacity_l && (
                <p className="text-sm text-destructive">{errors.tank_capacity_l.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="initial_odometer_km">Initial odometer (km)</Label>
              <Input
                id="initial_odometer_km"
                type="number"
                inputMode="decimal"
                step="0.1"
                {...register("initial_odometer_km")}
              />
            </div>
          </div>
          <Button type="submit" disabled={updateVehicle.isPending}>
            {updateVehicle.isPending ? "Saving…" : "Save vehicle details"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "New password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type PasswordValues = z.infer<typeof passwordSchema>;

function ChangePasswordCard() {
  const changePassword = useChangePassword();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) });

  const onSubmit = (values: PasswordValues) => {
    changePassword.mutate(
      { current_password: values.current_password, new_password: values.new_password },
      {
        onSuccess: () => {
          toast.success("Password changed");
          reset();
        },
        onError: (error) =>
          toast.error(error instanceof ApiError ? error.message : "Couldn't change password"),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Change password</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="current_password">Current password</Label>
            <Input
              id="current_password"
              type="password"
              autoComplete="current-password"
              {...register("current_password")}
            />
            {errors.current_password && (
              <p className="text-sm text-destructive">{errors.current_password.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              {...register("new_password")}
            />
            {errors.new_password && (
              <p className="text-sm text-destructive">{errors.new_password.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm_password">Confirm new password</Label>
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              {...register("confirm_password")}
            />
            {errors.confirm_password && (
              <p className="text-sm text-destructive">{errors.confirm_password.message}</p>
            )}
          </div>
          <Button type="submit" disabled={changePassword.isPending}>
            {changePassword.isPending ? "Saving…" : "Change password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-md space-y-4 p-4">
      <VehicleSettingsCard />
      <ChangePasswordCard />
    </div>
  );
}
