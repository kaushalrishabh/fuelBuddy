"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useForgotPassword } from "@/lib/queries/auth";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
});

type Values = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const forgotPassword = useForgotPassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center text-xl">Reset your password</CardTitle>
        </CardHeader>
        <CardContent>
          {forgotPassword.isSuccess ? (
            <p className="text-center text-sm text-muted-foreground">
              If that email is registered, a reset link is on its way. It&apos;s valid for 1 hour.
            </p>
          ) : (
            <form
              onSubmit={handleSubmit((values) => forgotPassword.mutate(values.email))}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" autoComplete="email" {...register("email")} />
                {errors.email && (
                  <p className="text-sm text-destructive">{errors.email.message}</p>
                )}
              </div>
              <Button type="submit" className="w-full" disabled={forgotPassword.isPending}>
                {forgotPassword.isPending ? "Sending…" : "Send reset link"}
              </Button>
            </form>
          )}
          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link href="/login" className="underline underline-offset-4">
              Back to sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
