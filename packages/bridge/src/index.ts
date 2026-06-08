/**
 * @shay/bridge
 *
 * External bridge layer: MCP client, A2A agent card protocol, OASF translation.
 * All external capability discovery flows through this package.
 */

export type { McpTool, McpTransport } from './mcp-client.js';
export { McpClient } from './mcp-client.js';

export type { AgentCard } from './a2a.js';
export { parseAgentCard, toCapabilityManifests, produceAgentCard } from './a2a.js';

export type { OasfDescriptor } from './oasf.js';
export { oasfToManifest, manifestToOasf } from './oasf.js';
