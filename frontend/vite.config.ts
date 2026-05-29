import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Expose on all network interfaces so the app is reachable from phones/other devices on the LAN
  // Port 3000 — avoid 5173; Windows Hyper-V often reserves 5146–5245 (EACCES on bind)
  server: {
    host: true,
    port: 3000,
  },
})
