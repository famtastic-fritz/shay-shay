import { EventBus } from './event-bus.js';

export enum TrustTier {
  Observe = 0,
  Suggest = 1,
  Draft = 2,
  Confirm = 3,
  Auto = 4,
}

export interface AuthorityOptions {
  manual: boolean;
}

/**
 * AuthorityRegistry tracks trust tiers for subjects and determines
 * what operations are permitted based on those tiers.
 */
export class AuthorityRegistry {
  private tiers: Map<string, TrustTier> = new Map();
  private eventBus?: EventBus;
  private defaultTier = TrustTier.Suggest;

  constructor(eventBus?: EventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Get the trust tier for a subject. Returns default (Suggest) if not set.
   */
  getTier(subject: string): TrustTier {
    return this.tiers.get(subject) ?? this.defaultTier;
  }

  /**
   * Set the trust tier for a subject.
   * @throws Error if opts.manual is false
   * @throws Error if opts is omitted
   */
  setTier(subject: string, tier: TrustTier, opts: AuthorityOptions): void {
    if (!opts || opts.manual !== true) {
      throw new Error(
        'setTier requires opts: { manual: true }'
      );
    }

    this.tiers.set(subject, tier);

    if (this.eventBus) {
      this.eventBus.emit({
        id: `auth_${Date.now()}`,
        type: 'authority:tier-changed',
        payload: { subject, tier },
        timestamp: new Date().toISOString(),
        source: 'AuthorityRegistry',
      });
    }
  }

  /**
   * Check if a subject can perform an operation at a given tier level.
   */
  can(subject: string, requiredTier: TrustTier): boolean {
    const subjectTier = this.getTier(subject);
    return subjectTier >= requiredTier;
  }

  /**
   * Promote a subject to a higher tier.
   * @throws Error if opts.manual is false
   */
  promote(subject: string, toTier: TrustTier, opts: AuthorityOptions): void {
    if (!opts || opts.manual !== true) {
      throw new Error(
        'promote requires opts: { manual: true }'
      );
    }

    this.tiers.set(subject, toTier);

    if (this.eventBus) {
      this.eventBus.emit({
        id: `auth_${Date.now()}`,
        type: 'authority:tier-changed',
        payload: { subject, tier: toTier },
        timestamp: new Date().toISOString(),
        source: 'AuthorityRegistry',
      });
    }
  }
}
