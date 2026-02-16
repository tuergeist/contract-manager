import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import type { ReactElement } from 'react'

interface MockUser {
  id: number
  email: string
  firstName: string
  lastName: string
  tenantId: number | null
  tenantName: string | null
  roleName: string | null
  isAdmin: boolean
  roles: string[]
  permissions: string[]
}

export function createMockUser(overrides: Partial<MockUser> = {}): MockUser {
  return {
    id: 1,
    email: 'test@test.local',
    firstName: 'Test',
    lastName: 'User',
    tenantId: 1,
    tenantName: 'Test Tenant',
    roleName: 'Admin',
    isAdmin: false,
    roles: [],
    permissions: [],
    ...overrides,
  }
}

interface RenderWithAuthOptions extends Omit<RenderOptions, 'wrapper'> {
  permissions?: string[]
  user?: Partial<MockUser>
  route?: string
}

/**
 * Render a component with mocked auth context and MemoryRouter.
 *
 * Before calling this, mock `@/lib/auth` in your test:
 * ```
 * vi.mock('@/lib/auth', () => ({ useAuth: vi.fn() }))
 * ```
 * Then call `setupAuthMock({ permissions: [...] })` before each render.
 */
export function setupAuthMock(options: { permissions?: string[]; user?: Partial<MockUser> } = {}) {
  const mockUser = createMockUser({
    permissions: options.permissions ?? [],
    ...options.user,
  })

  const { useAuth } = require('@/lib/auth')
  ;(useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    user: mockUser,
    token: 'mock-token',
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refetchUser: vi.fn(),
    hasPermission: (resource: string, action: string) =>
      mockUser.permissions.includes(`${resource}.${action}`),
  })
}

export function renderWithAuth(
  ui: ReactElement,
  { permissions, user, route = '/', ...renderOptions }: RenderWithAuthOptions = {}
) {
  setupAuthMock({ permissions, user })

  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[route]}>
        {children}
      </MemoryRouter>
    ),
    ...renderOptions,
  })
}
