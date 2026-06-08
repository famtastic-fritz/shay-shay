/**
 * @shay/surfaces — PhoneSurface adapter (Telegram-style messaging)
 *
 * Maps inbound platform updates (chatId + text) to SurfaceMessages and
 * formats replies. No Telegram SDK is used — the sender fn is injected by the
 * caller so this file has no third-party runtime dependency.
 *
 * Contains zero brain / memory logic.
 */

import type { GatewayClient, SurfaceMessage } from '../gateway-client.js';

// ---------------------------------------------------------------------------
// Platform update shape (Telegram-style, generic enough for other messengers)
// ---------------------------------------------------------------------------

/**
 * An inbound platform update — the minimal fields PhoneSurface needs.
 */
export interface PhoneUpdate {
  /** Platform-assigned chat identifier. */
  chatId: string | number;
  /** Text the user sent. */
  text: string;
  /** Optional caller-specific metadata (user id, username, …). */
  meta?: Record<string, unknown>;
}

/**
 * Injected function that sends a reply back to the platform.
 * The caller owns the SDK — PhoneSurface just calls this fn.
 */
export type PhoneSenderFn = (chatId: string | number, text: string) => Promise<void>;

// ---------------------------------------------------------------------------
// PhoneSurface
// ---------------------------------------------------------------------------

export interface PhoneSurfaceOptions {
  /** Surface label forwarded in every SurfaceMessage (defaults to 'phone'). */
  surface?: string;
}

/**
 * Phone / messaging surface adapter.
 *
 * Usage example (Telegram wiring omitted from this file):
 *
 *   const phone = new PhoneSurface(gatewayClient, bot.sendMessage.bind(bot));
 *   bot.on('message', (ctx) =>
 *     phone.dispatch({ chatId: ctx.chat.id, text: ctx.message.text ?? '' })
 *   );
 */
export class PhoneSurface {
  private readonly client: GatewayClient;
  private readonly sender: PhoneSenderFn;
  private readonly surface: string;
  private seq = 0;

  constructor(
    client: GatewayClient,
    sender: PhoneSenderFn,
    opts: PhoneSurfaceOptions = {}
  ) {
    this.client = client;
    this.sender = sender;
    this.surface = opts.surface ?? 'phone';
  }

  /**
   * Handle an inbound platform update: translate it to a SurfaceMessage, send
   * it to the gateway, format the reply, and deliver it via the injected
   * sender fn.
   *
   * Returns the reply text so callers can test without relying on side effects.
   */
  async dispatch(update: PhoneUpdate): Promise<string> {
    const msg: SurfaceMessage = {
      id: `phone-${++this.seq}-${Date.now()}`,
      text: update.text.trim(),
      surface: this.surface,
      meta: { chatId: update.chatId, ...update.meta },
    };

    const response = await this.client.send(msg);
    const replyText = this.format(response.text);
    await this.sender(update.chatId, replyText);
    return replyText;
  }

  /**
   * Format the gateway response text for the platform.
   * Override by subclassing or wrapping — this default is a pass-through.
   */
  protected format(text: string): string {
    return text;
  }
}
