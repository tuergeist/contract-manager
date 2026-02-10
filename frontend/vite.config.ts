import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 3000,
    allowedHosts: ['.ngrok-free.app', '.ngrok.io', '.ngrok.app'],
    proxy: {
      '/graphql': {
        target: 'http://backend:8000',  // Internal Docker network
        changeOrigin: true,
      },
      '/api': {
        target: 'http://backend:8000',  // Internal Docker network
        changeOrigin: true,
      },
      '/media': {
        target: 'http://backend:8000',  // Internal Docker network
        changeOrigin: true,
      },
    },
  },
})
