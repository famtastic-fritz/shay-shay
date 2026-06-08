/**
 * @shay/surfaces — public API
 *
 * Thin platform-adapter layer. Exports the GatewayClient contracts and all
 * four surface adapters. Zero brain / memory logic — surfaces only translate
 * platform I/O to/from GatewayClient.
 */

// Gateway contracts
export type {
  SurfaceMessage,
  SurfaceResponse,
  GatewayClient,
  GatewayTransport,
  BrainHandleFn,
} from './gateway-client.js';

export {
  LocalGatewayClient,
  RemoteGatewayClient,
  MockGatewayClient,
} from './gateway-client.js';

// Adapters
export { CliSurface } from './adapters/cli.js';
export type { CliSurfaceOptions } from './adapters/cli.js';

export { WebSurface } from './adapters/web.js';
export type {
  WebSurfaceOptions,
  HttpRequestLike,
  HttpResponseLike,
} from './adapters/web.js';

export { PhoneSurface } from './adapters/phone.js';
export type {
  PhoneSurfaceOptions,
  PhoneUpdate,
  PhoneSenderFn,
} from './adapters/phone.js';

export { McpSurface } from './adapters/mcp.js';
export type {
  McpSurfaceOptions,
  McpToolCall,
  McpToolResult,
} from './adapters/mcp.js';
