import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "NmapSLM — Network Scanner + AI",
  description: "Aplikasi scanning jaringan terintegrasi dengan analisis AI lokal menggunakan Ollama",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 h-screen overflow-hidden`}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1e293b",
              border: "1px solid #334155",
              color: "#e2e8f0",
            },
          }}
          theme="dark"
        />
      </body>
    </html>
  );
}
