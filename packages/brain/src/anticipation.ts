import { TrustTier, AuthorityRegistry } from '../../core/src/authority.js';

/**
 * Anticipation represents a predicted future state or action with confidence,
 * risk assessment, and routing information. Anticipations are derived from
 * turn outcomes and surfaced or queued based on confidence and TrustTier gating.
 */
export interface Anticipation {
  trigger: string;
  confidence: number;
  suggested_action: string;
  risk_level: 'low' | 'medium' | 'high';
  requires_confirmation: boolean;
  agent_to_route_to: string;
}

/**
 * TurnOutcome represents the outcome of a turn (interaction) that may
 * generate anticipations. Contains structured data about what happened
 * and contextual information for anticipation generation.
 */
export interface TurnOutcome {
  subject: string;
  action: string;
  result: unknown;
  context?: Record<string, unknown>;
}

/**
 * AnticipationResult is the output of AnticipationEngine.fromTurnOutcome().
 * Surfaced anticipations are high-confidence and ready to act on immediately.
 * Queued anticipations are lower-confidence and stored for later review.
 */
export interface AnticipationResult {
  surfaced: Anticipation[];
  queued: Anticipation[];
}

/**
 * AnticipationEngine generates anticipations from turn outcomes, applying
 * TrustTier-based gating to determine which anticipations are surfaced
 * (returned immediately) vs queued (stored silently).
 *
 * Gating logic:
 * - High-confidence anticipations (confidence >= 0.7) are always surfaced
 * - Lower-confidence anticipations are queued unless special conditions apply
 * - requires_confirmation is set based on TrustTier:
 *   - TrustTier.Suggest: all anticipations require confirmation
 *   - TrustTier.Observe: only high-risk anticipations require confirmation
 *   - TrustTier.Act: all anticipations require confirmation
 *   - TrustTier.Auto: only high-risk anticipations require confirmation
 */
export class AnticipationEngine {
  private authorityRegistry: AuthorityRegistry;

  constructor(authorityRegistry: AuthorityRegistry) {
    this.authorityRegistry = authorityRegistry;
  }

  /**
   * Generate anticipations from a turn outcome.
   * Returns surfaced anticipations (to display/act on immediately) and
   * queued anticipations (to store silently for later review).
   *
   * @param outcome The turn outcome to generate anticipations from
   * @param subject Optional override for the subject (uses outcome.subject if not provided)
   * @returns AnticipationResult with surfaced and queued anticipations
   */
  fromTurnOutcome(outcome: TurnOutcome, subject?: string): AnticipationResult {
    const effectiveSubject = subject ?? outcome.subject;
    const tier = this.authorityRegistry.getTier(effectiveSubject);

    // Generate raw candidate anticipations from the outcome
    const candidates = this.generateCandidates(outcome);

    // Apply gating logic based on confidence and TrustTier
    const surfaced: Anticipation[] = [];
    const queued: Anticipation[] = [];

    for (const candidate of candidates) {
      // Apply TrustTier-based confirmation requirement
      const withConfirmation = this.applyTrustTierGating(candidate, tier);

      // High-confidence anticipations are surfaced; others queued
      if (withConfirmation.confidence >= 0.7) {
        surfaced.push(withConfirmation);
      } else {
        queued.push(withConfirmation);
      }
    }

    return { surfaced, queued };
  }

  /**
   * Generate candidate anticipations from a turn outcome.
   * This is a placeholder implementation that can be extended
   * with domain-specific logic.
   */
  private generateCandidates(outcome: TurnOutcome): Anticipation[] {
    // Placeholder: return empty array
    // In a real implementation, this would analyze the outcome and generate
    // domain-specific anticipations based on patterns, history, etc.
    return [];
  }

  /**
   * Apply TrustTier-based gating to determine if an anticipation
   * requires confirmation.
   *
   * Gating logic:
   * - TrustTier.Suggest: requires confirmation for any risk_level
   * - TrustTier.Observe: requires confirmation only for 'high' risk
   * - TrustTier.Act: requires confirmation for all risk_levels
   * - TrustTier.Auto: requires confirmation only for 'high' risk
   */
  private applyTrustTierGating(
    anticipation: Anticipation,
    tier: TrustTier
  ): Anticipation {
    let requires_confirmation = anticipation.requires_confirmation;

    if (tier === TrustTier.Suggest) {
      // Suggest tier: always require confirmation
      requires_confirmation = true;
    } else if (tier === TrustTier.Observe || tier === TrustTier.Auto) {
      // Observe/Auto tiers: require confirmation only for high risk
      requires_confirmation = anticipation.risk_level === 'high';
    } else if (tier === TrustTier.Act) {
      // Act tier: always require confirmation
      requires_confirmation = true;
    }

    return {
      ...anticipation,
      requires_confirmation,
    };
  }
}
