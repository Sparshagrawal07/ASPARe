import type { Metadata } from "next";
import { AuthForm } from "@/components/auth/AuthForm";

export const metadata: Metadata = { title: "Create your account" };

export default function SignUpPage() {
  return <AuthForm mode="sign-up" />;
}
