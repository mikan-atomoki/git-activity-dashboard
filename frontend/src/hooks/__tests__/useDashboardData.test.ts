import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useDashboardData } from '../useDashboardData'

// ---------------------------------------------------------------------------
// Mock all dashboard API functions
// ---------------------------------------------------------------------------

vi.mock('@/lib/api/dashboard', () => ({
  getDashboardStats: vi.fn(),
  getCommitActivity: vi.fn(),
  getLanguageBreakdown: vi.fn(),
  getRepoBreakdown: vi.fn(),
  getHourlyHeatmap: vi.fn(),
  getTechTrends: vi.fn(),
  getCategoryBreakdown: vi.fn(),
}))

import {
  getDashboardStats,
  getCommitActivity,
  getLanguageBreakdown,
  getRepoBreakdown,
  getHourlyHeatmap,
  getTechTrends,
  getCategoryBreakdown,
} from '@/lib/api/dashboard'

// Cast to vi.Mock for type-safe usage
const mockGetDashboardStats = getDashboardStats as ReturnType<typeof vi.fn>
const mockGetCommitActivity = getCommitActivity as ReturnType<typeof vi.fn>
const mockGetLanguageBreakdown = getLanguageBreakdown as ReturnType<typeof vi.fn>
const mockGetRepoBreakdown = getRepoBreakdown as ReturnType<typeof vi.fn>
const mockGetHourlyHeatmap = getHourlyHeatmap as ReturnType<typeof vi.fn>
const mockGetTechTrends = getTechTrends as ReturnType<typeof vi.fn>
const mockGetCategoryBreakdown = getCategoryBreakdown as ReturnType<typeof vi.fn>

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockStats = {
  total_commits: 150,
  active_repos: 5,
  current_streak: 7,
  top_language: 'TypeScript',
  commit_change_pct: 12.5,
}

const mockCommits = {
  period: 'daily',
  data: [
    { date: '2026-02-10', count: 5, additions: 100, deletions: 20 },
    { date: '2026-02-11', count: 3, additions: 50, deletions: 10 },
  ],
  total_commits: 8,
}

const mockLanguages = {
  data: [
    { language: 'TypeScript', percentage: 60, color: '#3178c6' },
    { language: 'Python', percentage: 40, color: '#3572A5' },
  ],
}

const mockRepos = {
  data: [
    { repo_id: 1, repo_name: 'web_app', commit_count: 100, percentage: 66.7, primary_language: 'TypeScript' },
  ],
  total_commits: 150,
}

const mockHeatmap = {
  data: [
    { day_of_week: 1, hour: 10, count: 5 },
  ],
  max_count: 5,
}

const mockTechTrends = {
  data: [
    { period_start: '2026-02-01', tag: 'React', count: 10 },
  ],
}

const mockCategories = {
  data: [
    { category: 'feature', count: 20, percentage: 50 },
    { category: 'bugfix', count: 20, percentage: 50 },
  ],
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useDashboardData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts with loading true', () => {
    // Return promises that never resolve to keep loading state
    mockGetDashboardStats.mockReturnValue(new Promise(() => {}))
    mockGetCommitActivity.mockReturnValue(new Promise(() => {}))
    mockGetLanguageBreakdown.mockReturnValue(new Promise(() => {}))
    mockGetRepoBreakdown.mockReturnValue(new Promise(() => {}))
    mockGetHourlyHeatmap.mockReturnValue(new Promise(() => {}))
    mockGetTechTrends.mockReturnValue(new Promise(() => {}))
    mockGetCategoryBreakdown.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useDashboardData('daily'))

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBeNull()
    expect(result.current.commitTimeline).toEqual([])
  })

  it('loads all dashboard data successfully', async () => {
    mockGetDashboardStats.mockResolvedValue(mockStats)
    mockGetCommitActivity.mockResolvedValue(mockCommits)
    mockGetLanguageBreakdown.mockResolvedValue(mockLanguages)
    mockGetRepoBreakdown.mockResolvedValue(mockRepos)
    mockGetHourlyHeatmap.mockResolvedValue(mockHeatmap)
    mockGetTechTrends.mockResolvedValue(mockTechTrends)
    mockGetCategoryBreakdown.mockResolvedValue(mockCategories)

    const { result } = renderHook(() => useDashboardData('daily'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.commitTimeline).toEqual(mockCommits.data)
    expect(result.current.languages).toEqual(mockLanguages.data)
    expect(result.current.repos).toEqual({ data: mockRepos.data, total: mockRepos.total_commits })
    expect(result.current.heatmap).toEqual(mockHeatmap.data)
    expect(result.current.techTrends).toEqual(mockTechTrends.data)
    expect(result.current.categories).toEqual(mockCategories.data)
    expect(result.current.error).toBeNull()
  })

  it('passes period parameter to getCommitActivity', async () => {
    mockGetDashboardStats.mockResolvedValue(mockStats)
    mockGetCommitActivity.mockResolvedValue(mockCommits)
    mockGetLanguageBreakdown.mockResolvedValue(mockLanguages)
    mockGetRepoBreakdown.mockResolvedValue(mockRepos)
    mockGetHourlyHeatmap.mockResolvedValue(mockHeatmap)
    mockGetTechTrends.mockResolvedValue(mockTechTrends)
    mockGetCategoryBreakdown.mockResolvedValue(mockCategories)

    const { result } = renderHook(() => useDashboardData('weekly'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(mockGetCommitActivity).toHaveBeenCalledWith({ period: 'weekly' })
  })

  it('uses fallback values when individual API calls fail', async () => {
    mockGetDashboardStats.mockRejectedValue(new Error('fail'))
    mockGetCommitActivity.mockRejectedValue(new Error('fail'))
    mockGetLanguageBreakdown.mockRejectedValue(new Error('fail'))
    mockGetRepoBreakdown.mockRejectedValue(new Error('fail'))
    mockGetHourlyHeatmap.mockRejectedValue(new Error('fail'))
    mockGetTechTrends.mockRejectedValue(new Error('fail'))
    mockGetCategoryBreakdown.mockRejectedValue(new Error('fail'))

    const { result } = renderHook(() => useDashboardData('daily'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should use fallback values instead of setting error
    expect(result.current.stats).toEqual({
      total_commits: 0,
      active_repos: 0,
      current_streak: 0,
      top_language: null,
      commit_change_pct: null,
    })
    expect(result.current.commitTimeline).toEqual([])
    expect(result.current.languages).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('exposes a refresh function', async () => {
    mockGetDashboardStats.mockResolvedValue(mockStats)
    mockGetCommitActivity.mockResolvedValue(mockCommits)
    mockGetLanguageBreakdown.mockResolvedValue(mockLanguages)
    mockGetRepoBreakdown.mockResolvedValue(mockRepos)
    mockGetHourlyHeatmap.mockResolvedValue(mockHeatmap)
    mockGetTechTrends.mockResolvedValue(mockTechTrends)
    mockGetCategoryBreakdown.mockResolvedValue(mockCategories)

    const { result } = renderHook(() => useDashboardData('daily'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(typeof result.current.refresh).toBe('function')
  })
})
