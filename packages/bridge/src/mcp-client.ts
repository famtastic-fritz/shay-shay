/**
 * @shay/bridge — McpClient
 *
 * Thin client that adapts an MCP transport into CapabilityManifests.
 * All I/O goes through an injected McpTransport so tests can be hermetic.
 */

import { TrustTier } from '@shay/core';
import type { CapabilityManifest } from '@shay/capabilities';

/**
 * Minimal representation of a tool discovered from an MCP server.
 */
export interface McpTool {
  /** The tool's unique name within the MCP server. */
  name: string;
  /** Human-readable description. */
  description: string;
  /** Optional JSON Schema for the input arguments. */
  inputSchema?: Record<string, unknown>;
}

/**
 * Transport abstraction for MCP protocol I/O.
 * Inject a MockTransport in tests to avoid real network calls.
 */
export interface McpTransport {
  /** Retrieve the list of tools the MCP server exposes. */
  listTools(): Promise<McpTool[]>;
  /** Invoke a named tool with an argument bag. Returns the raw result. */
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
}

/**
 * McpClient wraps a McpTransport and exposes two operations:
 *
 * - `discoverCapabilities()` — queries the transport for its tool list and
 *   maps each tool to a CapabilityManifest (source: 'external', tier: Suggest).
 * - `callTool()` — proxies a tool call through to the transport.
 *
 * Trust tier for all MCP-discovered capabilities is TrustTier.Suggest (1),
 * consistent with the policy for externally-sourced capabilities.
 */
export class McpClient {
  private transport: McpTransport;

  constructor(transport: McpTransport) {
    this.transport = transport;
  }

  /**
   * Discover capabilities from the MCP server.
   * Maps each MCP tool to a CapabilityManifest with source:'external'.
   */
  async discoverCapabilities(): Promise<CapabilityManifest[]> {
    const tools = await this.transport.listTools();
    return tools.map((tool) => ({
      id: tool.name,
      version: '0.0.0',
      name: tool.name,
      description: tool.description ?? '',
      // Trust tier is metadata — stored by the registry, not on the manifest itself.
      // The caller is expected to register these with source:'external', TrustTier.Suggest.
    }));
  }

  /**
   * Call a tool through the MCP transport.
   */
  async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    return this.transport.callTool(name, args);
  }

  /** Expose the default external trust tier for callers that need it. */
  static readonly DEFAULT_TRUST_TIER: TrustTier = TrustTier.Suggest;
}
