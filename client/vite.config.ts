import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import { defineConfig, loadEnv } from "vite"

function documentCsp(apiOrigin: string, mode: string): string {
  const connect: string[] = ["'self'"]
  if (apiOrigin) connect.push(apiOrigin)
  if (mode === "development") {
    connect.push("ws://localhost:5173", "ws://127.0.0.1:5173", "http://localhost:3000")
  }
  const connectSrc = connect.join(" ")
  if (mode === "development") {
    return [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com data:",
      "img-src 'self' data: blob:",
      `connect-src ${connectSrc}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
    ].join("; ")
  }
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    `connect-src ${connectSrc}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
  ].join("; ")
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const rawApi = env.VITE_API_URL || ""
  const apiOrigin = rawApi.startsWith("http") ? new URL(rawApi).origin : ""
  const csp = documentCsp(apiOrigin, mode)

  return {
    plugins: [tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }), react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      headers: {
        "Content-Security-Policy": csp,
      },
    },
    preview: {
      headers: {
        "Content-Security-Policy": csp,
      },
    },
  }
})
