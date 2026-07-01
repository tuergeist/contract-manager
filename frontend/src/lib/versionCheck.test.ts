import { describe, it, expect } from 'vitest'
import { parseVersion, isNewer } from './versionCheck'

describe('parseVersion', () => {
  it('parses plain semver', () => {
    expect(parseVersion('2.34.12')).toEqual([2, 34, 12])
  })

  it('strips a v prefix', () => {
    expect(parseVersion('v1.0.0')).toEqual([1, 0, 0])
  })

  it('returns null for non-semver', () => {
    expect(parseVersion('dev')).toBeNull()
    expect(parseVersion('2.1')).toBeNull()
    expect(parseVersion('2.1.0-rc1')).toBeNull()
    expect(parseVersion('')).toBeNull()
    expect(parseVersion(null)).toBeNull()
    expect(parseVersion(undefined)).toBeNull()
  })
})

describe('isNewer', () => {
  it('true when latest patch is higher', () => {
    expect(isNewer('2.34.12', '2.34.11')).toBe(true)
  })

  it('true across minor and major', () => {
    expect(isNewer('2.35.0', '2.34.99')).toBe(true)
    expect(isNewer('3.0.0', '2.99.99')).toBe(true)
  })

  it('false when equal', () => {
    expect(isNewer('2.34.12', '2.34.12')).toBe(false)
  })

  it('false when latest is older', () => {
    expect(isNewer('2.34.10', '2.34.12')).toBe(false)
  })

  it('false when either version is not parseable (e.g. dev build)', () => {
    expect(isNewer('2.34.12', 'dev')).toBe(false)
    expect(isNewer(null, '2.34.12')).toBe(false)
    expect(isNewer(undefined, '2.34.12')).toBe(false)
  })
})
