/**
 * @shay/surfaces — McpSurface adapter
 *
 * Exposes Shay to MCP (Model Context Protocol) callers by mapping an inbound
 * MCP tool-call to a SurfaceMessage and returning an MCP-style result.
 *
 * No MCP SDK dependency — the shapes are plain objects matching the protocol
 * wire format. The caller owns SDK wiring.
 *
 * Contains zero brain / memory logic.
 */

import type { GatewayClient, SurfaceMessage } from '../gateway-client.js';

// ---------------------------------------------------------------------------
// MCP wire shapes (protocol-level, no SDK dependency)
// ---------------------------------------------------------------------------

/**
 * Inbound MCP tool call.
 */
export interface McpToolCall {
  /** MCP tool name (e.g. 'shay_ask'). */
  name: string;
  /** Tool arguments as a free-form object. */
  args: Record<string, unknown>;
  /** Optional correlation id assigned by the MCP host. */
  callId?: string;
}

/**
 * MCP tool result returned to the host.
 */
export interface McpToolResult {
  /** Mirrors McpToolCall.callId if provided. */
  callId?: string;
  /** MCP content array — at minimum a single text item. */
  content: Array<{ type: 'text'; text: string }>;
  /** True when the tool produced an error result. */
  isError?: boolean;
}

// ---------------------------------------------------------------------------
// McpSurface
// ---------------------------------------------------------------------------

export interface McpSurfaceOptions {
  /**
   * Name of the argument key that carries the user's text.
   * Defaults to 'text'. The surface also checks 'message' and 'prompt' as
   * fallbacks before returning a 400-style error result.
   */
  textArgKey?: string;
  /** Surface label forwarded in every SurfaceMessage (defaults to 'mcp'). */
  surface?: string;
}

/**
 * MCP surface adapter.
 *
 * Usage example (MCP SDK wiring omitted from this file):
 *
 *   const mcp = new McpSurface(gatewayClient);
 *   server.setRequestHandler(CallToolRequestSchema, async (req) =>
 *     mcp.call({ name: req.params.name, args: req.params.arguments ?? {} })
 *   );
 */
export class McpSurface {
  private readonly client: GatewayClient;
  private readonly textArgKey: string;
  private readonly surface: string;
  private seq = 0;

  constructor(client: GatewayClient, opts: McpSurfaceOptions = {}) {
    this.client = client;
    this.textArgKey = opts.textArgKey ?? 'text';
    this.surface = opts.surface ?? 'mcp';
  }

  /**
   * Map an MCP tool call to a SurfaceMessage, send it to the gateway, and
   * return an MCP-style result.
   */
  async call(toolCall: McpToolCall): Promise<McpToolResult> {
    const raw =
      toolCall.args[this.textArgKey] ??
      toolCall.args['message'] ??
      toolCall.args['prompt'];

    if (typeof raw !== 'string' || raw.trim() === '') {
      return {
        callId: toolCall.callId,
        content: [
          {
            type: 'text',
            text: `McpSurface: tool "${toolCall.name}" requires a non-empty "${this.textArgKey}" argument.`,
          },
        ],
        isError: true,
      };
    }

    const msg: SurfaceMessage = {
      id: `mcp-${++this.seq}-${Date.now()}`,
      text: raw.trim(),
      surface: this.surface,
      meta: {
        toolName: toolCall.name,
        callId: toolCall.callId,
        args: toolCall.args,
      },
    };

    const response = await this.client.send(msg);

    return {
      callId: toolCall.callId,
      content: [{ type: 'text', text: response.text }],
    };
  }
}
