import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "react-hot-toast";
import QueryProvider from "@/app/providers/QueryProvider";
import ThemeProvider from "@/app/providers/ThemeProvider";
import { AuthProvider } from "@/app/providers/AuthProvider";
import { FeatureFlagsProvider } from "@/app/providers/FeatureFlagsProvider";
import { WebSocketProvider } from "@/app/providers/WebSocketProvider";
import { RootErrorBoundary } from "@/shared/lib/ErrorBoundary";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "CreditFlow",
  description: "Платформа онлайн-кредитования",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="ru"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <RootErrorBoundary>
          <ThemeProvider>
            <QueryProvider>
              <AuthProvider>
                {/* DOC 6 §6: flags are personalized, so this must sit
                    below AuthProvider (access token already in memory)
                    and above anything that wants useFlag(). */}
                <FeatureFlagsProvider>
                  <WebSocketProvider>
                    {children}
                    <Toaster position="top-right" />
                  </WebSocketProvider>
                </FeatureFlagsProvider>
              </AuthProvider>
            </QueryProvider>
          </ThemeProvider>
        </RootErrorBoundary>
      </body>
    </html>
  );
}
