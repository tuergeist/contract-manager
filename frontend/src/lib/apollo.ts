import { ApolloClient, InMemoryCache, createHttpLink, from } from '@apollo/client'
import { setContext } from '@apollo/client/link/context'
import { onError } from '@apollo/client/link/error'

const httpLink = createHttpLink({
  uri: '/graphql',
  credentials: 'include',
})

const authLink = setContext((_, { headers }) => {
  const token = localStorage.getItem('auth_token')
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : '',
    },
  }
})

const errorLink = onError(({ graphQLErrors }) => {
  if (!graphQLErrors) return

  const hasAuthError = graphQLErrors.some(
    (err) => err.message === 'Authentication required'
  )

  if (hasAuthError && localStorage.getItem('auth_token')) {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
  }
})

export const apolloClient = new ApolloClient({
  link: from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
    },
  },
})
