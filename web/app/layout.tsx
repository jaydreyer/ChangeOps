import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChangeOps Policy Analysis",
  description: "Governed policy analysis from source language to controlled action",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
