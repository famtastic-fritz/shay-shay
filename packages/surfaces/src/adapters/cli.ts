/**
 * @shay/surfaces — CliSurface adapter
 *
 * Pure translation layer between a line of text input and the GatewayClient.
 * Contains zero brain / memory logic — it only maps a string in to a
 * SurfaceMessage and maps the SurfaceResponse back to a string out.
 *
 * The render() method is the core primitive: given an input string it
 * constructs a SurfaceMessage, sends it via the injected GatewayClient, and
 * returns the response text. Callers own the I/O (readline, stdin pipe, etc.).
 */

import type { GatewayClient, SurfaceMessage } from '../gateway-client.js';

// ---------------------------------------------------------------------------
// CliSurface
// ---------------------------------------------------------------------------

export interface CliSurfaceOptions {
  /** Surface label forwarded in every SurfaceMessage (defaults to 'cli'). */
  surface?: string;
  /** Optional callback invoked after a response is produced (e.g. stdout write). */
  onResponse?: (text: string) => void;
}

/**
 * CLI surface adapter.
 *
 * Usage example (wiring omitted from this file):
 *
 *   const cli = new CliSurface(gatewayClient);
 *   const reply = await cli.render('hello');
 *   process.stdout.write(reply + '\n');
 */
export class CliSurface {
  private readonly client: GatewayClient;
  private readonly surface: string;
  private readonly onResponse?: (text: string) => void;
  private seq = 0;

  constructor(client: GatewayClient, opts: CliSurfaceOptions = {}) {
    this.client = client;
    this.surface = opts.surface ?? 'cli';
    this.onResponse = opts.onResponse;
  }

  /**
   * Translate a raw input string to a SurfaceMessage, send it, and return
   * the response text. The caller decides how to obtain the input and where
   * to write the output.
   */
  async render(input: string): Promise<string> {
    const msg: SurfaceMessage = {
      id: `cli-${++this.seq}-${Date.now()}`,
      text: input.trim(),
      surface: this.surface,
    };
    const response = await this.client.send(msg);
    if (this.onResponse) this.onResponse(response.text);
    return response.text;
  }
}
