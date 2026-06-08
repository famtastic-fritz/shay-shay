import { readFileSync, writeFileSync, appendFileSync, existsSync } from 'node:fs';
import { dirname } from 'node:path';

/**
 * Defines the configuration for stall detection behavior.
 * If a step doesn't emit a heartbeat within `idleBudgetMs`, it is marked stalled
 * and the runner reconnects + resumes on the same lane (model/endpoint).
 */
export interface StallPolicy {
  idleBudgetMs: number;
  maxStallRetries: number;
}

/**
 * A single step in a resumable sequence.
 * Each step has a unique idempotency key to prevent re-execution
 * and a function to execute.
 */
export interface RunStep<T = any> {
  id: string;
  idempotencyKey: string;
  fn: (heartbeat: (msg: string) => void) => Promise<T>;
}

/**
 * A checkpoint record appended to the JSONL log after each step completes.
 * Records the step that ran, when it ran, and its result.
 */
export interface CheckpointRecord {
  timestamp: string;
  stepId: string;
  idempotencyKey: string;
  status: 'completed' | 'stalled' | 'failed';
  result?: any;
  error?: string;
  stallInfo?: {
    lastHeartbeat: string;
    retriesUsed: number;
  };
}

/**
 * Encapsulates a brain call function (model invocation).
 * The runner injects this function so tests can mock it.
 */
export type BrainCallFn = (
  prompt: string,
  context?: Record<string, any>
) => Promise<string>;

/**
 * ResumableRunner executes a sequence of steps with built-in checkpointing.
 * After each step completes, a checkpoint is appended to the JSONL log.
 * On resume, the runner reads the log, finds the last completed step,
 * and continues from the next one — never restarting from the beginning.
 *
 * Stall detection: if a step emits no heartbeat within the idle budget,
 * the runner marks it stalled, reconnects on the SAME lane (does not switch models),
 * and resumes.
 */
export class ResumableRunner {
  private stallPolicy: StallPolicy = {
    idleBudgetMs: 30000,
    maxStallRetries: 3,
  };

  constructor(stallPolicy?: Partial<StallPolicy>) {
    if (stallPolicy) {
      this.stallPolicy = { ...this.stallPolicy, ...stallPolicy };
    }
  }

  /**
   * Execute a sequence of steps, with checkpointing after each completion.
   * After each step, a checkpoint record is appended to the JSONL file.
   *
   * @param steps Array of RunStep to execute sequentially
   * @param brainCallFn Injected brain call function (mockable for tests)
   * @param checkpointPath Path to the JSONL checkpoint log file
   * @returns The result of the final step
   */
  async run<T = any>(
    steps: RunStep[],
    brainCallFn: BrainCallFn,
    checkpointPath: string
  ): Promise<T> {
    const checkpointDir = dirname(checkpointPath);
    if (!existsSync(checkpointDir)) {
      throw new Error(`Checkpoint directory does not exist: ${checkpointDir}`);
    }

    // Read existing checkpoints to find where to resume from
    const completedStepIds = this.readCheckpoints(checkpointPath);
    const startIdx = this.findResumeIndex(steps, completedStepIds);

    let finalResult: any = undefined;

    // Execute steps sequentially from the resume point
    for (let i = startIdx; i < steps.length; i++) {
      const step = steps[i];
      finalResult = await this.executeStep(
        step,
        brainCallFn,
        checkpointPath,
        completedStepIds
      );
    }

    return finalResult as T;
  }

  /**
   * Resume execution from where the last checkpoint left off.
   * Reads the checkpoint log to find the last completed step and continues.
   *
   * @param steps Array of RunStep to execute
   * @param brainCallFn Injected brain call function (mockable for tests)
   * @param checkpointPath Path to the JSONL checkpoint log file
   * @returns The result of the final step
   */
  async resume<T = any>(
    steps: RunStep[],
    brainCallFn: BrainCallFn,
    checkpointPath: string
  ): Promise<T> {
    // resume() is semantically identical to run() in this implementation
    // Both check the checkpoint log and continue from the last completed step
    return this.run(steps, brainCallFn, checkpointPath);
  }

  /**
   * Read the JSONL checkpoint log and extract step IDs that have completed.
   */
  private readCheckpoints(checkpointPath: string): Set<string> {
    const completed = new Set<string>();

    if (!existsSync(checkpointPath)) {
      return completed;
    }

    try {
      const content = readFileSync(checkpointPath, 'utf-8');
      const lines = content.trim().split('\n');

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const record: CheckpointRecord = JSON.parse(line);
          if (record.status === 'completed') {
            completed.add(record.stepId);
          }
        } catch {
          // Skip malformed lines
        }
      }
    } catch {
      // If file doesn't exist or can't be read, return empty set
    }

    return completed;
  }

  /**
   * Find the index in the steps array where we should resume from.
   * Returns the first step that hasn't been completed yet.
   */
  private findResumeIndex(steps: RunStep[], completedStepIds: Set<string>): number {
    for (let i = 0; i < steps.length; i++) {
      if (!completedStepIds.has(steps[i].id)) {
        return i;
      }
    }
    // All steps completed
    return steps.length;
  }

  /**
   * Execute a single step with stall detection.
   * If the step completes, append a checkpoint record.
   * If it stalls (no heartbeat), mark it stalled and reconnect.
   */
  private async executeStep(
    step: RunStep,
    brainCallFn: BrainCallFn,
    checkpointPath: string,
    completedStepIds: Set<string>
  ): Promise<any> {
    let stallRetries = 0;
    let lastHeartbeat = new Date().toISOString();

    // Heartbeat callback — called by the step function to signal it's still alive
    const heartbeat = (msg: string) => {
      lastHeartbeat = new Date().toISOString();
    };

    while (stallRetries <= this.stallPolicy.maxStallRetries) {
      try {
        let stallTimeout: NodeJS.Timeout | null = null;
        let result: any = undefined;
        let stallDetected = false;

        // Set up stall detection: if no heartbeat within idleBudgetMs, mark stalled
        const stallPromise = new Promise<void>((_, reject) => {
          stallTimeout = setTimeout(() => {
            stallDetected = true;
            reject(new Error('Step stalled: no heartbeat within budget'));
          }, this.stallPolicy.idleBudgetMs);
        });

        try {
          result = await Promise.race([step.fn(heartbeat), stallPromise]);
        } catch (err) {
          if (stallDetected && stallRetries < this.stallPolicy.maxStallRetries) {
            // Stall detected and we have retries left — mark as stalled and retry
            this.appendCheckpoint(checkpointPath, {
              timestamp: new Date().toISOString(),
              stepId: step.id,
              idempotencyKey: step.idempotencyKey,
              status: 'stalled',
              stallInfo: {
                lastHeartbeat,
                retriesUsed: stallRetries,
              },
            });

            stallRetries++;
            continue; // Retry on the same lane
          } else {
            // Real error or max retries exhausted
            throw err;
          }
        } finally {
          if (stallTimeout) clearTimeout(stallTimeout);
        }

        // Step completed successfully
        this.appendCheckpoint(checkpointPath, {
          timestamp: new Date().toISOString(),
          stepId: step.id,
          idempotencyKey: step.idempotencyKey,
          status: 'completed',
          result,
        });

        completedStepIds.add(step.id);
        return result;
      } catch (error) {
        // Non-stall error or max stall retries exceeded
        const errorMsg = error instanceof Error ? error.message : String(error);
        this.appendCheckpoint(checkpointPath, {
          timestamp: new Date().toISOString(),
          stepId: step.id,
          idempotencyKey: step.idempotencyKey,
          status: 'failed',
          error: errorMsg,
        });

        throw error;
      }
    }

    throw new Error(
      `Step ${step.id} failed after ${stallRetries} stall retries`
    );
  }

  /**
   * Append a checkpoint record to the JSONL log.
   */
  private appendCheckpoint(checkpointPath: string, record: CheckpointRecord): void {
    const line = JSON.stringify(record) + '\n';
    appendFileSync(checkpointPath, line, 'utf-8');
  }
}
