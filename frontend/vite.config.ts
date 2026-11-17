import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// BASE_PATH pozwala serwować aplikację z podkatalogu, np. /chemia/
const base = process.env.BASE_PATH || '/'

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 5180,
    proxy: { [`${base}api`]: { target: 'http://127.0.0.1:8010', rewrite: (p) => p.slice(base.length - 1) } },
  },
  build: { chunkSizeWarningLimit: 900 },
})
