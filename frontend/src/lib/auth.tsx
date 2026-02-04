import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useApolloClient, gql } from '@apollo/client'

interface User {
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

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  refetchUser: () => Promise<void>
  hasPermission: (resource: string, action: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const LOGIN_MUTATION = gql`
  mutation Login($email: String!, $password: String!) {
    login(email: $email, password: $password) {
      ... on AuthPayload {
        accessToken
        refreshToken
        userId
        email
        tenantId
      }
      ... on AuthError {
        message
      }
    }
  }
`

const ME_QUERY = gql`
  query Me {
    me {
      id
      email
      firstName
      lastName
      tenantId
      tenantName
      roleName
      isAdmin
      roles
      permissions
    }
  }
`

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [isLoading, setIsLoading] = useState(true)
  const client = useApolloClient()

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY)
      if (!storedToken) {
        setIsLoading(false)
        return
      }

      try {
        const { data } = await client.query({
          query: ME_QUERY,
          context: {
            headers: {
              Authorization: `Bearer ${storedToken}`,
            },
          },
          fetchPolicy: 'network-only',
        })

        if (data.me) {
          setUser(data.me)
          setToken(storedToken)
        } else {
          // Token invalid, clear storage
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(REFRESH_TOKEN_KEY)
          setToken(null)
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        setToken(null)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [client])

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const { data } = await client.mutate({
        mutation: LOGIN_MUTATION,
        variables: { email, password },
      })

      if (data.login.accessToken) {
        const { accessToken, refreshToken } = data.login
        localStorage.setItem(TOKEN_KEY, accessToken)
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
        setToken(accessToken)

        // Fetch user data
        const { data: userData } = await client.query({
          query: ME_QUERY,
          context: {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          },
          fetchPolicy: 'network-only',
        })

        if (userData.me) {
          setUser(userData.me)
        }

        return { success: true }
      } else {
        return { success: false, error: data.login.message }
      }
    } catch (error) {
      return { success: false, error: 'Login failed. Please try again.' }
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setToken(null)
    setUser(null)
    client.clearStore()
  }

  const hasPermission = (resource: string, action: string): boolean => {
    if (!user) return false
    return user.permissions.includes(`${resource}.${action}`)
  }

  const refetchUser = async () => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (!storedToken) return

    try {
      const { data } = await client.query({
        query: ME_QUERY,
        context: {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        },
        fetchPolicy: 'network-only',
      })

      if (data.me) {
        setUser(data.me)
      }
    } catch {
      // Ignore errors during refetch
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refetchUser,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
