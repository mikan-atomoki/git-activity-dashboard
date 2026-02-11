import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch, ApiError, getStoredToken, storeTokens, clearTokens } from '../client'

// ---------------------------------------------------------------------------
// Mock fetch globally
// ---------------------------------------------------------------------------

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------

const store: Record<string, string> = {}

const localStorageMock: Storage = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value },
  removeItem: (key: string) => { delete store[key] },
  clear: () => { Object.keys(store).forEach((k) => delete store[k]) },
  length: 0,
  key: () => null,
}

vi.stubGlobal('localStorage', localStorageMock)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
    headers: new Headers(),
  } as unknown as Response
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    localStorageMock.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -----------------------------------------------------------------------
  // Token persistence
  // -----------------------------------------------------------------------

  describe('token persistence', () => {
    it('stores and retrieves tokens', () => {
      storeTokens('access123', 'refresh456')
      expect(getStoredToken()).toBe('access123')
    })

    it('clears tokens', () => {
      storeTokens('access123', 'refresh456')
      clearTokens()
      expect(getStoredToken()).toBeNull()
    })
  })

  // -----------------------------------------------------------------------
  // apiFetch — basic behaviour
  // -----------------------------------------------------------------------

  describe('apiFetch', () => {
    it('sends GET request to the correct URL', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }))

      await apiFetch('/api/v1/dashboard/stats')

      expect(mockFetch).toHaveBeenCalledTimes(1)
      const [url] = mockFetch.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/v1/dashboard/stats')
    })

    it('includes Content-Type header by default', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }))

      await apiFetch('/api/v1/test')

      const [, options] = mockFetch.mock.calls[0]
      expect(options.headers['Content-Type']).toBe('application/json')
    })

    it('includes Authorization header when token is stored', async () => {
      storeTokens('my-jwt-token', 'my-refresh')
      mockFetch.mockResolvedValueOnce(jsonResponse({ data: 'secret' }))

      await apiFetch('/api/v1/secure')

      const [, options] = mockFetch.mock.calls[0]
      expect(options.headers['Authorization']).toBe('Bearer my-jwt-token')
    })

    it('does NOT include Authorization header when no token', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ data: 'public' }))

      await apiFetch('/api/v1/public')

      const [, options] = mockFetch.mock.calls[0]
      expect(options.headers['Authorization']).toBeUndefined()
    })

    it('returns parsed JSON on success', async () => {
      const payload = { total_commits: 42, active_repos: 5 }
      mockFetch.mockResolvedValueOnce(jsonResponse(payload))

      const result = await apiFetch('/api/v1/dashboard/stats')
      expect(result).toEqual(payload)
    })
  })

  // -----------------------------------------------------------------------
  // Error handling
  // -----------------------------------------------------------------------

  describe('error handling', () => {
    it('throws ApiError on 500 response', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Internal server error' }, 500),
      )

      try {
        await apiFetch('/api/v1/fail')
        expect.unreachable('should have thrown')
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(500)
        expect((err as ApiError).message).toBe('Internal server error')
      }
    })

    it('throws ApiError on 404 response', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Not found' }, 404),
      )

      try {
        await apiFetch('/api/v1/missing')
        expect.unreachable('should have thrown')
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(404)
        expect((err as ApiError).message).toBe('Not found')
      }
    })

    it('handles non-JSON error bodies gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 502,
        statusText: 'Bad Gateway',
        json: () => Promise.reject(new Error('not json')),
        headers: new Headers(),
      } as unknown as Response)

      try {
        await apiFetch('/api/v1/bad-gateway')
        expect.unreachable('should have thrown')
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(502)
        expect((err as ApiError).message).toBe('Bad Gateway')
      }
    })
  })

  // -----------------------------------------------------------------------
  // Auto-refresh on 401
  // -----------------------------------------------------------------------

  describe('auto-refresh on 401', () => {
    it('attempts token refresh and retries on 401', async () => {
      storeTokens('expired-token', 'valid-refresh')

      // First call: 401
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Token expired' }, 401),
      )
      // Refresh call: success
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ access_token: 'new-token', refresh_token: 'new-refresh' }),
      )
      // Retry call: success
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ data: 'refreshed' }),
      )

      const result = await apiFetch('/api/v1/secure')

      expect(result).toEqual({ data: 'refreshed' })
      // 3 calls total: original, refresh, retry
      expect(mockFetch).toHaveBeenCalledTimes(3)
    })

    it('throws ApiError when refresh also fails', async () => {
      storeTokens('expired-token', 'bad-refresh')

      // First call: 401
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Token expired' }, 401),
      )
      // Refresh call: also fails
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid refresh token' }, 401),
      )

      try {
        await apiFetch('/api/v1/secure')
        expect.unreachable('should have thrown')
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError)
        expect((err as ApiError).status).toBe(401)
      }
    })
  })
})
