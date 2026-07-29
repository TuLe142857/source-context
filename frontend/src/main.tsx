import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider as ReduxProvider } from 'react-redux'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { store } from '@/store'
import { queryClient } from '@/lib/queryClient'
import { Toaster } from '@/components/ui/sonner'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ReduxProvider store={store}>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster theme="dark" position="top-right" richColors />
      </QueryClientProvider>
    </ReduxProvider>
  </StrictMode>,
)
