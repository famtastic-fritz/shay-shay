/**
 * @shay/bridge — McpClient tests (hermetic, MockTransport)
 */

import { describe, it, expect } from 'vitest';
import { McpClient } from '../src/mcp-client.js';
import type { McpTransport, McpTool } from '../src/mcp-client.js';
import { TrustTier } from '@shay/core';

/** Hermetic mock — no real network calls. */
function makeMockTransport(tools: McpTool[]): McpTransport {
  return {
    async listTools() { return tools; },
    async callTool(name, args) { return { called: name, args }; },
  };
}

describe('McpClient.discoverCapabilities()', () => {
  it('maps MCP tools to CapabilityManifests', async () => {
    const transport = makeMockTransport([
      { name: 'search', description: 'Search the web' },
      { name: 'summarize', description: 'Summarize text' },
    ]);
    const client = new McpClient(transport);
    const manifests = await client.discoverCapabilities();

    expect(manifests).toHaveLength(2);
    expect(manifests[0].id).toBe('search');
    expect(manifests[0].name).toBe('search');
    expect(manifests[0].description).toBe('Search the web');
    expect(manifests[1].id).toBe('summarize');
  });

  it('returns an empty array when transport has no tools', async () => {
    const client = new McpClient(makeMockTransport([]));
    const manifests = await client.discoverCapabilities();
    expect(manifests).toHaveLength(0);
  });

  it('handles tools without a description by defaulting to empty string', async () => {
    const transport = makeMockTransport([{ name: 'no-desc', description: '' }]);
    const client = new McpClient(transport);
    const [manifest] = await client.discoverCapabilities();
    expect(manifest.description).toBe('');
  });
});

describe('McpClient.callTool()', () => {
  it('proxies callTool through the transport', async () => {
    const transport = makeMockTransport([]);
    const client = new McpClient(transport);
    const result = await client.callTool('search', { q: 'hello' });
    expect(result).toEqual({ called: 'search', args: { q: 'hello' } });
  });
});

describe('McpClient.DEFAULT_TRUST_TIER', () => {
  it('is TrustTier.Suggest', () => {
    expect(McpClient.DEFAULT_TRUST_TIER).toBe(TrustTier.Suggest);
  });
});
