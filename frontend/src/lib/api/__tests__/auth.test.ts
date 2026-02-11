import { describe, it, expect, vi, beforeEach } from 'vitest'
import { login, register } from '../auth'

// ---------------------------------------------------------------------------
// Mock fetch globally
// ---------------------------------------------------------------------------

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

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

describe('Auth API', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  // -----------------------------------------------------------------------
  // login
  // -----------------------------------------------------------------------

  describe('login', () => {
    it('sends POST to /api/v1/auth/login with URL-encoded body', async () => {
      const tokenRes = {
        access_token: 'jwt-access',
        refresh_token: 'jwt-refresh',
        token_type: 'bearer',
        expires_in: 3600,
      }
      mockFetch.mockResolvedValueOnce(jsonResponse(tokenRes))

      const result = await login('mikan', 'testpass123')

      expect(result).toEqual(tokenRes)
      expect(mockFetch).toHaveBeenCalledTimes(1)

      const [url, options] = mockFetch.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/v1/auth/login')
      expect(options.method).toBe('POST')
      expect(options.headers['Content-Type']).toBe(
        'application/x-www-form-urlencoded',
      )

      // body is URLSearchParams
      const bodyStr = options.body.toString()
      expect(bodyStr).toContain('username=mikan')
      expect(bodyStr).toContain('password=testpass123')
    })

    it('throws Error on failed login', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Invalid credentials' }, 401),
      )

      await expect(login('bad', 'wrong')).rejects.toThrow('Invalid credentials')
    })

    it('throws generic message when response has no detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('not json')),
        headers: new Headers(),
      } as unknown as Response)

      await expect(login('user', 'pass')).rejects.toThrow('Internal Server Error')
    })
  })

  // -----------------------------------------------------------------------
  // register
  // -----------------------------------------------------------------------

  describe('register', () => {
    it('sends POST to /api/v1/auth/register with JSON body', async () => {
      const authRes = {
        user: {
          user_id: 1,
          github_login: 'mikan',
          display_name: null,
          avatar_url: null,
          created_at: '2026-01-01T00:00:00Z',
        },
        access_token: 'jwt-access',
        refresh_token: 'jwt-refresh',
      }
      mockFetch.mockResolvedValueOnce(jsonResponse(authRes))

      const result = await register('mikan', 'testpass123')

      expect(result).toEqual(authRes)
      expect(mockFetch).toHaveBeenCalledTimes(1)

      const [url, options] = mockFetch.mock.calls[0]
      expect(url).toBe('http://localhost:8000/api/v1/auth/register')
      expect(options.method).toBe('POST')
      expect(options.headers['Content-Type']).toBe('application/json')

      const body = JSON.parse(options.body)
      expect(body.username).toBe('mikan')
      expect(body.password).toBe('testpass123')
      expect(body.email).toBeNull()
    })

    it('includes email when provided', async () => {
      const authRes = {
        user: {
          user_id: 2,
          github_login: 'other',
          display_name: null,
          avatar_url: null,
          created_at: '2026-01-01T00:00:00Z',
        },
        access_token: 'jwt-access',
        refresh_token: 'jwt-refresh',
      }
      mockFetch.mockResolvedValueOnce(jsonResponse(authRes))

      await register('other', 'pass', 'other@example.com')

      const body = JSON.parse(mockFetch.mock.calls[0][1].body)
      expect(body.email).toBe('other@example.com')
    })

    it('throws Error on failed registration', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Username already exists' }, 409),
      )

      await expect(register('taken', 'pass')).rejects.toThrow(
        'Username already exists',
      )
    })
  })
})
