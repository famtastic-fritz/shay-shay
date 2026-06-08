/**
 * Connector (MCP) Health Check
 *
 * Verifies @shay/bridge McpClient transport reachability through:
 * 1. Call ctx.mcp.discoverCapabilities()
 * 2. Assert it resolves without throwing
 * 3. On success, return count of discovered capabilities
 */

import type { HealthCheck, CheckResult, DoctorContext } from '../types.js';

const connectorCheckImpl: HealthCheck = {
  name: 'MCP Transport Reachability',
  domain: 'connector',

  async run(ctx: DoctorContext): Promise<CheckResult> {
    if (!ctx.mcp) {
      return {
        name: this.name,
        domain: this.domain,
        status: 'warn',
        detail: 'McpClient not provided in context',
        remediation: 'verify MCP server is running and transport is configured',
      };
    }

    try {
      const mcp = ctx.mcp;

      // Call discoverCapabilities with a timeout to avoid hanging
      if (typeof mcp.discoverCapabilities !== 'function') {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'McpClient does not expose discoverCapabilities() method',
          remediation: 'verify MCP server is running and transport is configured',
        };
      }

      const discoveryPromise = mcp.discoverCapabilities();

      // Add a reasonable timeout (5 seconds)
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('MCP discovery timeout after 5s')), 5000)
      );

      const capabilities = await Promise.race([discoveryPromise, timeoutPromise]);

      // Verify we got an array back
      if (!Array.isArray(capabilities)) {
        return {
          name: this.name,
          domain: this.domain,
          status: 'fail',
          detail: 'McpClient.discoverCapabilities() did not return an array',
          remediation: 'verify MCP server is running and transport is configured',
        };
      }

      return {
        name: this.name,
        domain: this.domain,
        status: 'pass',
        detail: `MCP transport is reachable (${capabilities.length} capabilities discovered)`,
      };
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      return {
        name: this.name,
        domain: this.domain,
        status: 'fail',
        detail: `MCP transport unreachable: ${errMsg}`,
        remediation: 'verify MCP server is running and transport is configured',
      };
    }
  },
};

export const connectorCheck = (ctx: DoctorContext): Promise<CheckResult> => connectorCheckImpl.run(ctx);
