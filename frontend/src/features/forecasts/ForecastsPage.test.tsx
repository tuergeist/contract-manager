import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ForecastsPage } from './ForecastsPage'

// Mock child components to avoid Apollo dependency
vi.mock('@/features/forecast/RevenueForecast', () => ({
  RevenueForecast: () => <div data-testid="revenue-forecast">RevenueForecast</div>,
}))

vi.mock('@/features/liquidity', () => ({
  LiquidityForecast: () => <div data-testid="liquidity-forecast">LiquidityForecast</div>,
}))

// Mock auth
vi.mock('@/lib/auth', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '@/lib/auth'

function mockAuth(permissions: string[]) {
  ;(useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    user: { id: 1, permissions },
    hasPermission: (resource: string, action: string) =>
      permissions.includes(`${resource}.${action}`),
    isAuthenticated: true,
    isLoading: false,
    token: 'mock',
    login: vi.fn(),
    logout: vi.fn(),
    refetchUser: vi.fn(),
  })
}

function renderPage(route = '/forecasts') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ForecastsPage />
    </MemoryRouter>
  )
}

describe('ForecastsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders only RevenueForecast without banking permission (no tabs)', () => {
    mockAuth([])
    renderPage()

    expect(screen.getByTestId('revenue-forecast')).toBeInTheDocument()
    expect(screen.queryByTestId('liquidity-forecast')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
  })

  it('renders tabs when user has banking.read permission', () => {
    mockAuth(['banking.read'])
    renderPage()

    expect(screen.getAllByRole('tab')).toHaveLength(2)
  })

  it('shows revenue tab active by default', () => {
    mockAuth(['banking.read'])
    renderPage()

    const revenueTab = screen.getByRole('tab', { name: /revenue/i })
    expect(revenueTab).toHaveAttribute('data-state', 'active')
    expect(screen.getByTestId('revenue-forecast')).toBeInTheDocument()
  })

  it('shows liquidity tab active from URL param', () => {
    mockAuth(['banking.read'])
    renderPage('/forecasts?tab=liquidity')

    const liquidityTab = screen.getByRole('tab', { name: /liquidity/i })
    expect(liquidityTab).toHaveAttribute('data-state', 'active')
    expect(screen.getByTestId('liquidity-forecast')).toBeInTheDocument()
  })
})
