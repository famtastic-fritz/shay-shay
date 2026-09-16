import { spawn } from 'node:child_process'

export interface LaunchResult {
  code: null | number
  error?: string
}

export const resolveShayBin = (env: NodeJS.ProcessEnv = process.env) => env.SHAY_BIN?.trim() || 'shay'

export const launchShayCommand = (args: string[]): Promise<LaunchResult> =>
  new Promise(resolve => {
    const child = spawn(resolveShayBin(), args, { stdio: 'inherit' })

    child.on('error', err => resolve({ code: null, error: err.message }))
    child.on('exit', code => resolve({ code }))
  })
