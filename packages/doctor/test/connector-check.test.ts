/**
 * Hermetic tests for connectorCheck.
 *
 * Tests verify:
 * - HEALTHY fixture: McpClient with MockTransport returning fixed tool list, status === 'pass'
 * - FAULTY fixture: MockTransport whose listTools() rejects, status === 'fail'
 * - Strictly disjoint test groups
 */

import { describe, it, expect } from 'vitest';
import { connectorCheck } from '../src/checks/connector-check.js';
import type { DoctorContext } from '../src/checks/types.js';
import { McpClient } from '@shay/bridge';
import type { McpTransport, McpTool } from '@shay/bridge';

describe('connector-check', () => {
  describe('healthy', () => {
    it('should pass with MockTransport returning valid tools', async () => {
      const tools: McpTool[] = [
        {
          name: 'test-tool-1',
          description: 'A test tool',
        },
        {
          name: 'test-tool-2',
          description: 'Another test tool',
        },
      ];

      const mockTransport: McpTransport = {
        listTools: async () => tools,
        callTool: async () => ({ success: true }),
      };

      const mcpClient = new McpClient(mockTransport);

      const ctx: DoctorContext = {
        mcp: mcpClient,
      };

      const result = await connectorCheck(ctx);

      expect(result.status).toBe('pass');
      expect(result.detail).toContain('2');
      expect(result.remediation).toBeUndefined();
    });
  });

  describe('faulty', () => {
    it('should fail when listTools() rejects', async () => {
      const mockTransport: McpTransport = {
        listTools: async () => {
          throw new Error('Network error');
        },
        callTool: async () => ({ success: true }),
      };

      const mcpClient = new McpClient(mockTransport);

      const ctx: DoctorContext = {
        mcp: mcpClient,
      };

      const result = await connectorCheck(ctx);

      expect(result.status).toBe('fail');
      expect(result.detail).toContain('Network error');
      expect(result.remediation).toBeDefined();
    });

    it('should fail when transport is not available', async () => {
      const ctx: DoctorContext = {
        mcp: undefined,
      };

      const result = await connectorCheck(ctx);

      expect(result.status).toBe('warn');
      expect(result.detail).toContain('not provided');
    });
  });
});
