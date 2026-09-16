import { EventEmitter } from 'node:events'

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { spawn } from 'node:child_process'

import { launchShayCommand, resolveShayBin } from '../lib/externalCli.js'

vi.mock('node:child_process', () => ({
  spawn: vi.fn()
}))

const spawnMock = vi.mocked(spawn)

describe('external CLI launcher', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses the SHAY_BIN override and falls back to shay', () => {
    expect(resolveShayBin({ SHAY_BIN: ' /opt/shay ' })).toBe('/opt/shay')
    expect(resolveShayBin({})).toBe('shay')
    expect(resolveShayBin({ SHAY_BIN: '   ' })).toBe('shay')
  })

  it('launches setup with inherited stdio and returns its exit code', async () => {
    const child = new EventEmitter()
    spawnMock.mockReturnValue(child as ReturnType<typeof spawn>)

    const resultPromise = launchShayCommand(['setup', '--non-interactive'])
    expect(spawnMock).toHaveBeenCalledWith(
      'shay',
      ['setup', '--non-interactive'],
      { stdio: 'inherit' }
    )

    child.emit('exit', 0)
    await expect(resultPromise).resolves.toEqual({ code: 0 })
  })

  it('reports a process launch error', async () => {
    const child = new EventEmitter()
    spawnMock.mockReturnValue(child as ReturnType<typeof spawn>)

    const resultPromise = launchShayCommand(['setup'])
    child.emit('error', new Error('shay unavailable'))

    await expect(resultPromise).resolves.toEqual({ code: null, error: 'shay unavailable' })
  })
})
