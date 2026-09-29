import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRouter } from '../router/index'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:  30_000,
      retry:      (failureCount, error: unknown) => {
        const status = (error as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

export function AppProviders() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
    </QueryClientProvider>
  )
}
