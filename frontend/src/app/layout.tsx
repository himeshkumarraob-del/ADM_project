import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AppProvider } from "@/lib/app-context";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Saarathi AI | Ancient wisdom. Modern guidance.",
  description:
    "A guide for reflecting on life's dilemmas through the Mahabharata attributed to Veda Vyasa.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <div className="shell">
            <Sidebar />
            <main className="main">{children}</main>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
