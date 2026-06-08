import { describe, it, expect, beforeEach } from 'vitest';

/**
 * Lane types supported by BrainRouter
 */
export enum LaneType {
  Subscription = 'subscription',
  Local = 'local',
  Metered = 'metered',
}

/**
 * Status returned by a brain call function
 */
export enum BrainStatus {
  Available = 'available',
  Unavailable = 'unavailable',
  CapExhausted = 'cap-exhausted',
}

/**
 * Response from a brain call function
 */
export interface BrainCallResult {
  status: BrainStatus;
  tokens?: number;
  error?: string;
}

/**
 * A lane in the router capable of processing requests
 */
export interface BrainLane {
  type: LaneType;
  call: (request: string) => Promise<BrainCallResult>;
  capRemaining?: number;
}

/**
 * BrainRouter routes requests to the best available lane
 */
export class BrainRouter {
  private lanes: BrainLane[] = [];
  private capTracking: Map<LaneType, number> = new Map();

  /**
   * Register a lane. Lanes are prioritized in registration order
   * after type-based prioritization (subscription > local > metered).
   */
  registerLane(lane: BrainLane): void {
    this.lanes.push(lane);
    if (lane.capRemaining !== undefined) {
      this.capTracking.set(lane.type, lane.capRemaining);
    }
  }

  /**
   * Route a request to the best available lane.
   * Prioritizes: subscription > local > metered.
   * Returns the first lane that returns 'available' status.
   * Skips lanes with 'unavailable' or 'cap-exhausted' status.
   * Does NOT failover if status is 'long' or any other custom status.
   */
  async route(request: string): Promise<BrainCallResult> {
    // Sort lanes by type priority: subscription (0) > local (1) > metered (2)
    const priorityMap: Record<LaneType, number> = {
      [LaneType.Subscription]: 0,
      [LaneType.Local]: 1,
      [LaneType.Metered]: 2,
    };

    const sortedLanes = [...this.lanes].sort(
      (a, b) => priorityMap[a.type] - priorityMap[b.type]
    );

    for (const lane of sortedLanes) {
      const result = await lane.call(request);

      // Failover only on specific statuses: unavailable or cap-exhausted
      if (result.status === BrainStatus.Unavailable || result.status === BrainStatus.CapExhausted) {
        continue;
      }

      // For any other status (including 'available' or custom statuses), return immediately
      if (result.status !== BrainStatus.Unavailable && result.status !== BrainStatus.CapExhausted) {
        // Track cap usage if this is a metered lane
        if (lane.type === LaneType.Metered && result.tokens !== undefined) {
          const current = this.capTracking.get(LaneType.Metered) ?? 0;
          const updated = current - result.tokens;
          this.capTracking.set(LaneType.Metered, updated);
        }
        return result;
      }
    }

    // All lanes exhausted or unavailable
    return {
      status: BrainStatus.CapExhausted,
      error: 'All lanes exhausted or unavailable',
    };
  }

  /**
   * Get remaining cap for a lane type
   */
  getCapRemaining(type: LaneType): number {
    return this.capTracking.get(type) ?? 0;
  }
}

describe('BrainRouter', () => {
  let router: BrainRouter;

  beforeEach(() => {
    router = new BrainRouter();
  });

  it('subscription lane is selected over local and metered regardless of registration order', async () => {
    const callSequence: string[] = [];

    // Register in this order: metered, local, subscription
    // (i.e., not in priority order)
    router.registerLane({
      type: LaneType.Metered,
      call: async (request: string) => {
        callSequence.push('metered');
        return { status: BrainStatus.Available, tokens: 10 };
      },
    });

    router.registerLane({
      type: LaneType.Local,
      call: async (request: string) => {
        callSequence.push('local');
        return { status: BrainStatus.Available };
      },
    });

    router.registerLane({
      type: LaneType.Subscription,
      call: async (request: string) => {
        callSequence.push('subscription');
        return { status: BrainStatus.Available };
      },
    });

    const result = await router.route('test request');

    expect(result.status).toBe(BrainStatus.Available);
    expect(callSequence).toEqual(['subscription']);
  });

  it('local is selected over metered when no subscription is available', async () => {
    const callSequence: string[] = [];

    // Register metered first, then local (but local should still be prioritized)
    router.registerLane({
      type: LaneType.Metered,
      call: async (request: string) => {
        callSequence.push('metered');
        return { status: BrainStatus.Available, tokens: 10 };
      },
    });

    router.registerLane({
      type: LaneType.Local,
      call: async (request: string) => {
        callSequence.push('local');
        return { status: BrainStatus.Available };
      },
    });

    const result = await router.route('test request');

    expect(result.status).toBe(BrainStatus.Available);
    expect(callSequence).toEqual(['local']);
  });

  it('failover occurs when a lane returns unavailable or cap-exhausted but NOT when the request is long', async () => {
    const callSequence: string[] = [];

    router.registerLane({
      type: LaneType.Local,
      call: async (request: string) => {
        callSequence.push('local');
        return { status: 'long' as BrainStatus }; // Custom status 'long'
      },
    });

    router.registerLane({
      type: LaneType.Metered,
      call: async (request: string) => {
        callSequence.push('metered');
        return { status: BrainStatus.Available, tokens: 10 };
      },
    });

    const result = await router.route('test request');

    // Should return 'long' status WITHOUT failover (local was tried first, returned 'long', no failover)
    expect(result.status).toBe('long' as BrainStatus);
    expect(callSequence).toEqual(['local']);
  });

  it('cap tracking increments and blocks exhausted lanes', async () => {
    // Register metered lane with limited cap
    router.registerLane({
      type: LaneType.Metered,
      call: async (request: string) => {
        const remaining = router.getCapRemaining(LaneType.Metered);
        if (remaining < 5) {
          return { status: BrainStatus.CapExhausted };
        }
        return { status: BrainStatus.Available, tokens: 10 };
      },
      capRemaining: 20,
    });

    // First call: metered has cap 20, uses 10, leaves 10
    let result = await router.route('request 1');
    expect(result.status).toBe(BrainStatus.Available);
    expect(router.getCapRemaining(LaneType.Metered)).toBe(10);

    // Second call: metered has cap 10, uses 10, leaves 0
    result = await router.route('request 2');
    expect(result.status).toBe(BrainStatus.Available);
    expect(router.getCapRemaining(LaneType.Metered)).toBe(0);

    // Now register a local lane as fallback
    router.registerLane({
      type: LaneType.Local,
      call: async (request: string) => {
        return { status: BrainStatus.Available };
      },
    });

    // Third call: metered cap is 0, returns cap-exhausted, falls back to local
    result = await router.route('request 3');
    expect(result.status).toBe(BrainStatus.Available);
  });
});
