/**
 * @shay/surfaces — Hermetic test suite
 *
 * 32 vitest tests across 5 strictly-disjoint groups:
 *   1. MockGatewayClient — send records messages, subscribe/unsubscribe, push (6 tests)
 *   2. LocalGatewayClient — calls injected handle fn, id + text forwarded (4 tests)
 *   3. RemoteGatewayClient — delegates to transport, rejects malformed response (5 tests)
 *   4. Adapters — CliSurface, WebSurface, PhoneSurface, McpSurface forward messages
 *      and render responses correctly (14 tests)
 *   5. No @shay/brain / @shay/memory imports — surfaces only import @shay/core
 *      types + GatewayClient (3 tests)
 *
 * All hermetic — MockGatewayClient only; no network calls.
 */

import { describe, it, expect, vi } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  MockGatewayClient,
  LocalGatewayClient,
  RemoteGatewayClient,
} from '../src/gateway-client.js';
import type {
  SurfaceMessage,
  SurfaceResponse,
  GatewayTransport,
} from '../src/gateway-client.js';
import { CliSurface } from '../src/adapters/cli.js';
import { WebSurface } from '../src/adapters/web.js';
import { PhoneSurface } from '../src/adapters/phone.js';
import { McpSurface } from '../src/adapters/mcp.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Group 1: MockGatewayClient
// ---------------------------------------------------------------------------

describe('MockGatewayClient', () => {
  it('records messages in the sent array', async () => {
    const mock = new MockGatewayClient();
    const msg: SurfaceMessage = { id: 'a1', text: 'hello', surface: 'cli' };
    await mock.send(msg);
    expect(mock.sent).toHaveLength(1);
    expect(mock.sent[0]).toEqual(msg);
  });

  it('returns a default reply keyed on the input text', async () => {
    const mock = new MockGatewayClient();
    const resp = await mock.send({ id: 'a2', text: 'ping', surface: 'cli' });
    expect(resp.text).toContain('ping');
    expect(resp.id).toBe('a2');
  });

  it('allows overriding the reply factory', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'pong' });
    const resp = await mock.send({ id: 'a3', text: 'any', surface: 'web' });
    expect(resp.text).toBe('pong');
  });

  it('subscribe delivers pushed responses to the handler', () => {
    const mock = new MockGatewayClient();
    const received: SurfaceResponse[] = [];
    mock.subscribe((r) => received.push(r));
    mock.push({ id: 'a4', text: 'streamed' });
    expect(received).toHaveLength(1);
    expect(received[0].text).toBe('streamed');
  });

  it('unsubscribe stops the handler from receiving further responses', () => {
    const mock = new MockGatewayClient();
    const received: SurfaceResponse[] = [];
    const unsub = mock.subscribe((r) => received.push(r));
    unsub();
    mock.push({ id: 'a5', text: 'after-unsub' });
    expect(received).toHaveLength(0);
  });

  it('records multiple messages in order', async () => {
    const mock = new MockGatewayClient();
    await mock.send({ id: 'a6a', text: 'first', surface: 'cli' });
    await mock.send({ id: 'a6b', text: 'second', surface: 'cli' });
    expect(mock.sent[0].id).toBe('a6a');
    expect(mock.sent[1].id).toBe('a6b');
  });
});

// ---------------------------------------------------------------------------
// Group 2: LocalGatewayClient
// ---------------------------------------------------------------------------

describe('LocalGatewayClient', () => {
  it('calls the injected handle fn', async () => {
    const spy = vi.fn(async (m: SurfaceMessage): Promise<SurfaceResponse> => ({
      id: m.id,
      text: 'handled',
    }));
    const client = new LocalGatewayClient(spy);
    await client.send({ id: 'b1', text: 'test', surface: 'cli' });
    expect(spy).toHaveBeenCalledOnce();
  });

  it('forwards the message id to the handle fn', async () => {
    let received: SurfaceMessage | undefined;
    const handle = async (m: SurfaceMessage): Promise<SurfaceResponse> => {
      received = m;
      return { id: m.id, text: 'ok' };
    };
    const client = new LocalGatewayClient(handle);
    await client.send({ id: 'b2', text: 'forwarded', surface: 'web' });
    expect(received?.id).toBe('b2');
  });

  it('returns the response produced by the handle fn', async () => {
    const handle = async (m: SurfaceMessage): Promise<SurfaceResponse> => ({
      id: m.id,
      text: 'brain reply',
      meta: { lane: 'subscription' },
    });
    const client = new LocalGatewayClient(handle);
    const resp = await client.send({ id: 'b3', text: 'q', surface: 'cli' });
    expect(resp.text).toBe('brain reply');
    expect(resp.meta?.['lane']).toBe('subscription');
  });

  it('propagates errors thrown by the handle fn', async () => {
    const handle = async (): Promise<SurfaceResponse> => {
      throw new Error('handle exploded');
    };
    const client = new LocalGatewayClient(handle);
    await expect(
      client.send({ id: 'b4', text: 'boom', surface: 'cli' })
    ).rejects.toThrow('handle exploded');
  });
});

// ---------------------------------------------------------------------------
// Group 3: RemoteGatewayClient
// ---------------------------------------------------------------------------

describe('RemoteGatewayClient', () => {
  it('delegates the payload to the injected transport', async () => {
    const transport: GatewayTransport = {
      request: vi.fn(async () => ({ id: 'c1', text: 'remote reply' })),
    };
    const client = new RemoteGatewayClient(transport);
    await client.send({ id: 'c1', text: 'hello remote', surface: 'web' });
    expect(transport.request).toHaveBeenCalledOnce();
  });

  it('returns the response returned by the transport', async () => {
    const transport: GatewayTransport = {
      request: async () => ({ id: 'c2', text: 'from server' }),
    };
    const client = new RemoteGatewayClient(transport);
    const resp = await client.send({ id: 'c2', text: 'q', surface: 'cli' });
    expect(resp.text).toBe('from server');
  });

  it('throws when the transport returns null', async () => {
    const transport: GatewayTransport = { request: async () => null };
    const client = new RemoteGatewayClient(transport);
    await expect(
      client.send({ id: 'c3', text: 'x', surface: 'cli' })
    ).rejects.toThrow(/invalid SurfaceResponse/);
  });

  it('throws when the transport response is missing the text field', async () => {
    const transport: GatewayTransport = {
      request: async () => ({ id: 'c4' }), // missing text
    };
    const client = new RemoteGatewayClient(transport);
    await expect(
      client.send({ id: 'c4', text: 'x', surface: 'cli' })
    ).rejects.toThrow(/invalid SurfaceResponse/);
  });

  it('forwards transport errors unchanged', async () => {
    const transport: GatewayTransport = {
      request: async () => {
        throw new Error('network down');
      },
    };
    const client = new RemoteGatewayClient(transport);
    await expect(
      client.send({ id: 'c5', text: 'x', surface: 'cli' })
    ).rejects.toThrow('network down');
  });
});

// ---------------------------------------------------------------------------
// Group 4: Adapters
// ---------------------------------------------------------------------------

describe('CliSurface', () => {
  it('sends a SurfaceMessage with surface=cli', async () => {
    const mock = new MockGatewayClient();
    const cli = new CliSurface(mock);
    await cli.render('hello');
    expect(mock.sent[0].surface).toBe('cli');
  });

  it('returns the response text', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'ack' });
    const cli = new CliSurface(mock);
    const result = await cli.render('any');
    expect(result).toBe('ack');
  });

  it('trims the input before sending', async () => {
    const mock = new MockGatewayClient();
    const cli = new CliSurface(mock);
    await cli.render('  trimmed  ');
    expect(mock.sent[0].text).toBe('trimmed');
  });

  it('calls the onResponse callback if provided', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'cb-reply' });
    const captured: string[] = [];
    const cli = new CliSurface(mock, { onResponse: (t) => captured.push(t) });
    await cli.render('go');
    expect(captured).toEqual(['cb-reply']);
  });
});

describe('WebSurface', () => {
  it('returns 405 for non-POST requests', async () => {
    const mock = new MockGatewayClient();
    const web = new WebSurface(mock);
    const resp = await web.handle({ method: 'GET', path: '/chat' });
    expect(resp.status).toBe(405);
    expect(mock.sent).toHaveLength(0);
  });

  it('returns 400 when body.text is absent', async () => {
    const mock = new MockGatewayClient();
    const web = new WebSurface(mock);
    const resp = await web.handle({ method: 'POST', path: '/chat', body: {} });
    expect(resp.status).toBe(400);
  });

  it('forwards body.text to the gateway and returns 200', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'web-reply' });
    const web = new WebSurface(mock);
    const resp = await web.handle({
      method: 'POST',
      path: '/chat',
      body: { text: 'ask something' },
    });
    expect(resp.status).toBe(200);
    expect((resp.body as Record<string, unknown>)['text']).toBe('web-reply');
  });

  it('includes response meta in the body when present', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({
      id: m.id,
      text: 'ok',
      meta: { tokens: 42 },
    });
    const web = new WebSurface(mock);
    const resp = await web.handle({
      method: 'POST',
      path: '/chat',
      body: { text: 'ping' },
    });
    expect((resp.body as Record<string, unknown>)['meta']).toEqual({ tokens: 42 });
  });
});

describe('PhoneSurface', () => {
  it('calls the sender fn with the formatted reply', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'hi there' });
    const sent: Array<[string | number, string]> = [];
    const phone = new PhoneSurface(mock, async (chatId, text) => {
      sent.push([chatId, text]);
    });
    await phone.dispatch({ chatId: 'u123', text: 'hello' });
    expect(sent).toHaveLength(1);
    expect(sent[0]).toEqual(['u123', 'hi there']);
  });

  it('includes chatId in SurfaceMessage meta', async () => {
    const mock = new MockGatewayClient();
    const phone = new PhoneSurface(mock, async () => undefined);
    await phone.dispatch({ chatId: 99, text: 'msg' });
    expect(mock.sent[0].meta?.['chatId']).toBe(99);
  });

  it('returns the reply text from dispatch()', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'reply-text' });
    const phone = new PhoneSurface(mock, async () => undefined);
    const result = await phone.dispatch({ chatId: '1', text: 'test' });
    expect(result).toBe('reply-text');
  });
});

describe('McpSurface', () => {
  it('maps a tool call text arg to a SurfaceMessage', async () => {
    const mock = new MockGatewayClient();
    const mcp = new McpSurface(mock);
    await mcp.call({ name: 'shay_ask', args: { text: 'what time is it' } });
    expect(mock.sent[0].text).toBe('what time is it');
    expect(mock.sent[0].surface).toBe('mcp');
  });

  it('returns an MCP result with a content array', async () => {
    const mock = new MockGatewayClient();
    mock.replyWith = (m) => ({ id: m.id, text: 'mcp response' });
    const mcp = new McpSurface(mock);
    const result = await mcp.call({ name: 'shay_ask', args: { text: 'q' } });
    expect(result.content[0].type).toBe('text');
    expect(result.content[0].text).toBe('mcp response');
    expect(result.isError).toBeFalsy();
  });

  it('returns an error result when the text arg is missing', async () => {
    const mock = new MockGatewayClient();
    const mcp = new McpSurface(mock);
    const result = await mcp.call({ name: 'shay_ask', args: {} });
    expect(result.isError).toBe(true);
    expect(mock.sent).toHaveLength(0);
  });

  it('falls back to "message" arg when "text" is absent', async () => {
    const mock = new MockGatewayClient();
    const mcp = new McpSurface(mock);
    await mcp.call({ name: 'shay_ask', args: { message: 'fallback text' } });
    expect(mock.sent[0].text).toBe('fallback text');
  });
});

// ---------------------------------------------------------------------------
// Group 5: No @shay/brain / @shay/memory imports
// ---------------------------------------------------------------------------

describe('Surfaces import isolation', () => {
  const surfacesSrc = path.resolve(__dirname, '../src');

  function collectSourceFiles(dir: string): string[] {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files: string[] = [];
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) files.push(...collectSourceFiles(full));
      else if (e.name.endsWith('.ts') && !e.name.endsWith('.test.ts'))
        files.push(full);
    }
    return files;
  }

  function hasActualImport(content: string, packageName: string): boolean {
    // Match import/export statements only, excluding comments
    const importRegex =
      /^(?!\/\/|\/\*)[^'"`]*(?:import|export)[^'"`]*["']@shay\/[^"']+["']/m;
    return importRegex.test(content);
  }

  it('no @shay/surfaces source file imports @shay/brain', () => {
    const files = collectSourceFiles(surfacesSrc);
    const violations = files.filter((f) => {
      const content = fs.readFileSync(f, 'utf-8');
      // Check for actual imports/exports, not just string presence
      return /(?:import|export).*from\s+['"]@shay\/brain['"]/.test(content);
    });
    expect(violations).toHaveLength(0);
  });

  it('no @shay/surfaces source file imports @shay/memory', () => {
    const files = collectSourceFiles(surfacesSrc);
    const violations = files.filter((f) => {
      const content = fs.readFileSync(f, 'utf-8');
      // Check for actual imports/exports, not just string presence
      return /(?:import|export).*from\s+['"]@shay\/memory['"]/.test(content);
    });
    expect(violations).toHaveLength(0);
  });

  it('index.ts exports GatewayClient, CliSurface, WebSurface, PhoneSurface, McpSurface', () => {
    const indexContent = fs.readFileSync(
      path.join(surfacesSrc, 'index.ts'),
      'utf-8'
    );
    expect(indexContent).toContain('GatewayClient');
    expect(indexContent).toContain('CliSurface');
    expect(indexContent).toContain('WebSurface');
    expect(indexContent).toContain('PhoneSurface');
    expect(indexContent).toContain('McpSurface');
  });
});
