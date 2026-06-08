/**
 * BrainRouter — Lane registration + subscription-first routing + cap tracking
 *
 * Defines Lane (id, kind, priority, capState, call fn) and BrainRouter.
 * registerLane() stores lanes. route(request) selects the highest-priority
 * available lane using subscription→local→metered ordering; failover only on
 * availability (lane down, unauthorized, cap-exhausted), never on request length.
 * Tracks cap usage per lane.
 */

/**
 * Represents the current capacity state of a lane
 */
export interface CapState {
  available: number;
  used: number;
  limit: number;
  resetAt?: number; // Unix timestamp for metered lanes
}

/**
 * Type of lane: subscription (high priority), local (medium), or metered (low, capped)
 */
export type LaneKind = 'subscription' | 'local' | 'metered';

/**
 * A request to the brain subsystem
 */
export interface BrainRequest {
  id: string;
  prompt: string;
  contextItems: Array<{
    id: string;
    priority: number;
    tokens: number;
  }>;
  laneHint?: string;
  maxTokens?: number;
}

/**
 * A response from the brain subsystem
 */
export interface BrainResponse {
  id: string;
  requestId: string;
  content: string;
  laneUsed: string; // The lane that processed this request
  tokensUsed: number;
  timestamp: number;
}

/**
 * Represents a registered lane with its configuration and call function
 */
export interface Lane {
  id: string;
  kind: LaneKind;
  priority: number; // Higher number = higher priority
  capState: CapState;
  call: (req: BrainRequest) => Promise<BrainResponse>;
  isAvailable(): boolean;
  isCapExhausted(): boolean;
  updateCapUsage(tokens: number): void;
}

/**
 * BrainRouter — manages multiple lanes with subscription-first routing
 */
export class BrainRouter {
  private lanes: Map<string, Lane> = new Map();
  private lanesByKind: Map<LaneKind, Lane[]> = new Map();

  constructor() {
    this.lanesByKind.set('subscription', []);
    this.lanesByKind.set('local', []);
    this.lanesByKind.set('metered', []);
  }

  /**
   * Register a new lane with the router
   */
  registerLane(lane: Lane): void {
    if (this.lanes.has(lane.id)) {
      throw new Error(`Lane ${lane.id} already registered`);
    }
    this.lanes.set(lane.id, lane);
    const kindLanes = this.lanesByKind.get(lane.kind) || [];
    kindLanes.push(lane);
    // Sort by priority (descending)
    kindLanes.sort((a, b) => b.priority - a.priority);
    this.lanesByKind.set(lane.kind, kindLanes);
  }

  /**
   * Get a registered lane by ID
   */
  getLane(id: string): Lane | undefined {
    return this.lanes.get(id);
  }

  /**
   * Get all registered lanes
   */
  getAllLanes(): Lane[] {
    return Array.from(this.lanes.values());
  }

  /**
   * Route a request to the highest-priority available lane
   *
   * Selection order: subscription → local → metered
   * Failover only on availability (lane down, unauthorized, cap-exhausted),
   * never on request length.
   */
  async route(request: BrainRequest): Promise<BrainResponse> {
    // If a laneHint is provided, try it first
    if (request.laneHint) {
      const hintedLane = this.lanes.get(request.laneHint);
      if (hintedLane && hintedLane.isAvailable() && !hintedLane.isCapExhausted()) {
        try {
          const response = await hintedLane.call(request);
          hintedLane.updateCapUsage(response.tokensUsed);
          return response;
        } catch {
          // Fall through to normal routing if hinted lane fails
        }
      }
    }

    // Try subscription lanes first (highest priority)
    const subscriptionLanes = this.lanesByKind.get('subscription') || [];
    for (const lane of subscriptionLanes) {
      if (lane.isAvailable() && !lane.isCapExhausted()) {
        const response = await lane.call(request);
        lane.updateCapUsage(response.tokensUsed);
        return response;
      }
    }

    // Try local lanes (medium priority)
    const localLanes = this.lanesByKind.get('local') || [];
    for (const lane of localLanes) {
      if (lane.isAvailable() && !lane.isCapExhausted()) {
        const response = await lane.call(request);
        lane.updateCapUsage(response.tokensUsed);
        return response;
      }
    }

    // Try metered lanes (lowest priority)
    const meteredLanes = this.lanesByKind.get('metered') || [];
    for (const lane of meteredLanes) {
      if (lane.isAvailable() && !lane.isCapExhausted()) {
        const response = await lane.call(request);
        lane.updateCapUsage(response.tokensUsed);
        return response;
      }
    }

    throw new Error('No available lanes to handle request');
  }

  /**
   * Get routing statistics
   */
  getStats(): {
    totalLanes: number;
    lanes: Array<{
      id: string;
      kind: LaneKind;
      priority: number;
      available: boolean;
      capExhausted: boolean;
      capUsage: number;
    }>;
  } {
    return {
      totalLanes: this.lanes.size,
      lanes: Array.from(this.lanes.values()).map((lane) => ({
        id: lane.id,
        kind: lane.kind,
        priority: lane.priority,
        available: lane.isAvailable(),
        capExhausted: lane.isCapExhausted(),
        capUsage: (lane.capState.used / lane.capState.limit) * 100,
      })),
    };
  }
}

/**
 * Create a mock lane for testing
 */
export function createMockLane(
  id: string,
  kind: LaneKind,
  priority: number,
  callFn?: (req: BrainRequest) => Promise<BrainResponse>,
): Lane {
  const capState: CapState = {
    available: 1000000,
    used: 0,
    limit: 1000000,
  };

  const defaultCall = async (req: BrainRequest): Promise<BrainResponse> => ({
    id: `response-${Date.now()}`,
    requestId: req.id,
    content: `Mock response for lane ${id}`,
    laneUsed: id,
    tokensUsed: 100,
    timestamp: Date.now(),
  });

  const call = callFn || defaultCall;

  return {
    id,
    kind,
    priority,
    capState,
    call,
    isAvailable(): boolean {
      return true;
    },
    isCapExhausted(): boolean {
      return this.capState.used >= this.capState.limit;
    },
    updateCapUsage(tokens: number): void {
      this.capState.used += tokens;
      this.capState.available = Math.max(0, this.capState.limit - this.capState.used);
    },
  };
}
