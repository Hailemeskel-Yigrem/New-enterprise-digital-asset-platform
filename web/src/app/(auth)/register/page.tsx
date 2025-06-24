"use client";

import { login, register } from "@/lib/api/auth";
import { registerSchema, type RegisterFormValues } from "@/lib/validators/auth";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { zodResolver } from "@hookform/resolvers/zod";
import { Shield } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

export default function RegisterPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const {
    register: registerField,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterFormValues) => {
    try {
      await register(data);
      await login({ email: data.email, password: data.password });
      await refreshUser();
      router.push("/dashboard");
    } catch (e) {
      setError("root", {
        message: e instanceof Error ? e.message : "Registration failed",
      });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-vault-950 vault-pattern px-4">
      <div className="w-full max-w-md rounded-xl border border-vault-700 bg-vault-900/80 p-8 shadow-2xl backdrop-blur">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-teal-950/50 ring-1 ring-teal-700/50">
            <Shield className="h-6 w-6 text-teal-400" />
          </div>
          <h1 className="font-serif text-2xl text-slate-100">Create account</h1>
          <p className="mt-1 text-sm text-slate-400">Start securing your digital assets</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Full name"
            autoComplete="name"
            error={errors.full_name?.message}
            {...registerField("full_name")}
          />
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...registerField("email")}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...registerField("password")}
          />
          <Input
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            error={errors.confirm_password?.message}
            {...registerField("confirm_password")}
          />
          {errors.root && (
            <p className="text-sm text-red-400">{errors.root.message}</p>
          )}
          <Button type="submit" className="w-full" isLoading={isSubmitting}>
            Create account
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="text-teal-400 hover:text-teal-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
