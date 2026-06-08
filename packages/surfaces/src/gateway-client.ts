/**
 * @shay/surfaces — GatewayClient contracts
 *
 * Defines the wire-level message/response shapes and three GatewayClient
 * implementations:
 *   - LocalGatewayClient  — in-process; wraps an injected handle fn
 *   - RemoteGatewayClient — out-of-process; wraps an injected transport
 *   - MockGatewayClient   — hermetic test double
 *
 * No brain or memory logic lives here. The handle fn and transport are
 * injected by the caller so this package carries zero coupling to any
 * logic packages (all deps are injected).
 */

// ---------------------------------------------------------------------------
// Wire types
// ---------------------------------------------------------------------------

/**
 * A message sent from any surface to the gateway.
 */
export interface SurfaceMessage {
  /** Caller-assigned correlation id. */
  id: string;
  /** Human-readable text payload. */
  text: string;
  /** Originating surface identifier (e.g. 'cli', 'web', 'phone', 'mcp'). */
  surface: string;
  /** Optional caller-provided metadata (platform-specific). */
  meta?: Record<string, unknown>;
}

/**
 * A response from the gateway back to a surface.
 */
export interface SurfaceResponse {
  /** Mirrors the SurfaceMessage id for correlation. */
  id: string;
  /** Text payload to render on the surface. */
  text: string;
  /** Optional gateway-provided metadata. */
  meta?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// GatewayClient interface
// ---------------------------------------------------------------------------

/**
 * Thin contract that every surface uses to talk to the gateway.
 * Surfaces must only depend on this interface — never on concrete brain types.
 */
export interface GatewayClient {
  /**
   * Send a message and await a single response.
   */
  send(msg: SurfaceMessage): Promise<SurfaceResponse>;

  /**
   * Optional push-subscription for streaming or event-driven surfaces.
   * Returns an unsubscribe fn.
   */
  subscribe?(handler: (response: SurfaceResponse) => void): () => void;
}

// ---------------------------------------------------------------------------
// Transport abstraction (used by RemoteGatewayClient)
// ---------------------------------------------------------------------------

/**
 * Minimal transport contract — HTTP, WebSocket, IPC — injected by the caller.
 * RemoteGatewayClient never knows whether it is talking over HTTP or WS.
 */
export interface GatewayTransport {
  request(payload: unknown): Promise<unknown>;
}

// ---------------------------------------------------------------------------
// LocalGatewayClient
// ---------------------------------------------------------------------------

/**
 * Handle fn signature — the gateway's entry point injected at construction time.
 * Typed loosely so this package carries no coupling to logic packages.
 */
export type BrainHandleFn = (msg: SurfaceMessage) => Promise<SurfaceResponse>;

/**
 * In-process gateway client for development surfaces or embedded use.
 * Calls the injected brain handle fn directly — no network required.
 */
export class LocalGatewayClient implements GatewayClient {
  private readonly handle: BrainHandleFn;

  constructor(handle: BrainHandleFn) {
    this.handle = handle;
  }

  async send(msg: SurfaceMessage): Promise<SurfaceResponse> {
    return this.handle(msg);
  }
}

// ---------------------------------------------------------------------------
// RemoteGatewayClient
// ---------------------------------------------------------------------------

/**
 * Out-of-process gateway client. Delegates every send() to an injected
 * transport (HTTP fetch wrapper, WS adapter, etc.) and casts the result.
 *
 * The transport is responsible for serialization. This class only validates
 * that the response shape has the required fields.
 */
export class RemoteGatewayClient implements GatewayClient {
  private readonly transport: GatewayTransport;

  constructor(transport: GatewayTransport) {
    this.transport = transport;
  }

  async send(msg: SurfaceMessage): Promise<SurfaceResponse> {
    const raw = await this.transport.request(msg);
    if (
      raw == null ||
      typeof raw !== 'object' ||
      typeof (raw as Record<string, unknown>)['id'] !== 'string' ||
      typeof (raw as Record<string, unknown>)['text'] !== 'string'
    ) {
      throw new Error(
        `RemoteGatewayClient: transport returned an invalid SurfaceResponse shape`
      );
    }
    return raw as SurfaceResponse;
  }
}

// ---------------------------------------------------------------------------
// MockGatewayClient
// ---------------------------------------------------------------------------

/**
 * Hermetic test double. Records every sent message and returns a configurable
 * reply. Supports subscribe() so streaming-surface tests can validate handler
 * wiring.
 */
export class MockGatewayClient implements GatewayClient {
  /** All messages received via send(), in order. */
  readonly sent: SurfaceMessage[] = [];

  /** All subscribe() handlers registered. */
  private readonly handlers: Array<(r: SurfaceResponse) => void> = [];

  /**
   * Factory for the reply returned by send().
   * Override in tests for error-path or custom-payload scenarios.
   */
  replyWith: (msg: SurfaceMessage) => SurfaceResponse = (msg) => ({
    id: msg.id,
    text: `mock reply to: ${msg.text}`,
  });

  async send(msg: SurfaceMessage): Promise<SurfaceResponse> {
    this.sent.push(msg);
    return this.replyWith(msg);
  }

  subscribe(handler: (response: SurfaceResponse) => void): () => void {
    this.handlers.push(handler);
    return () => {
      const idx = this.handlers.indexOf(handler);
      if (idx !== -1) this.handlers.splice(idx, 1);
    };
  }

  /** Push a response to all registered subscribe() handlers (test helper). */
  push(response: SurfaceResponse): void {
    for (const h of this.handlers) h(response);
  }
}
