import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChangeOps Approval Workbench",
  description: "Human review of proposed ChangeOps actions",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
