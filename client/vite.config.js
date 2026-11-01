import {defineConfig} from 'vite';

export default defineConfig({
  server: {
    allowedHosts: ['terminal.local'],
    proxy: {'/api': 'http://localhost:3001'}
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          icons: ['lucide-react']
        }
      }
    }
  }
});

