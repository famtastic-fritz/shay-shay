/**
 * @shay/surfaces — WebSurface adapter
 *
 * Framework-agnostic HTTP request-handler factory. No Express, Fastify, or
 * fetch dependency — the caller provides plain-object request/response shapes
 * and wires the framework adapter around this.
 *
 * Contains zero brain / memory logic. It maps an HTTP-ish request object to a
 * SurfaceMessage, forwards it to the injected GatewayClient, and maps the
 * SurfaceResponse back to an HTTP-ish response object.
 */

import type { GatewayClient, SurfaceMessage } from '../gateway-client.js';

// ---------------------------------------------------------------------------
// Framework-agnostic HTTP shapes
// ---------------------------------------------------------------------------

/**
 * Minimal representation of an inbound HTTP request.
 * Callers extract the fields they need and hand this to WebSurface.
 */
export interface HttpRequestLike {
  /** HTTP method (GET, POST, …). */
  method: string;
  /** Request path. */
  path: string;
  /** Parsed request body — callers are responsible for JSON deserialization. */
  body?: Record<string, unknown>;
  /** Request headers. */
  headers?: Record<string, string>;
}

/**
 * Minimal representation of an outbound HTTP response.
 */
export interface HttpResponseLike {
  /** HTTP status code. */
  status: number;
  /** JSON-serializable body. */
  body: Record<string, unknown>;
  /** Response headers. */
  headers?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// WebSurface
// ---------------------------------------------------------------------------

export interface WebSurfaceOptions {
  /** Surface label forwarded in every SurfaceMessage (defaults to 'web'). */
  surface?: string;
}

/**
 * Web surface adapter.
 *
 * Usage example (Express wiring omitted from this file):
 *
 *   const web = new WebSurface(gatewayClient);
 *   app.post('/chat', async (req, res) => {
 *     const result = await web.handle({ method: req.method, path: req.path, body: req.body });
 *     res.status(result.status).json(result.body);
 *   });
 */
export class WebSurface {
  private readonly client: GatewayClient;
  private readonly surface: string;
  private seq = 0;

  constructor(client: GatewayClient, opts: WebSurfaceOptions = {}) {
    this.client = client;
    this.surface = opts.surface ?? 'web';
  }

  /**
   * Map an HTTP-ish request to a SurfaceMessage, send it, and return an
   * HTTP-ish response. Only POST requests with a non-empty body.text are
   * forwarded; other requests receive a 400.
   */
  async handle(req: HttpRequestLike): Promise<HttpResponseLike> {
    if (req.method.toUpperCase() !== 'POST') {
      return {
        status: 405,
        body: { error: 'Method not allowed. Use POST.' },
      };
    }

    const text =
      typeof req.body?.['text'] === 'string' ? (req.body['text'] as string).trim() : '';

    if (!text) {
      return {
        status: 400,
        body: { error: 'Request body must include a non-empty "text" field.' },
      };
    }

    const msg: SurfaceMessage = {
      id: `web-${++this.seq}-${Date.now()}`,
      text,
      surface: this.surface,
      meta: req.body?.['meta'] as Record<string, unknown> | undefined,
    };

    const response = await this.client.send(msg);

    return {
      status: 200,
      body: { id: response.id, text: response.text, meta: response.meta },
      headers: { 'Content-Type': 'application/json' },
    };
  }
}
