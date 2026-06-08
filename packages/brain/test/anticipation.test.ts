import { describe, it, expect, beforeEach } from 'vitest';
import { AuthorityRegistry, TrustTier } from '../../core/src/authority.js';

/**
 * Risk level for an anticipated action
 */
export enum RiskLevel {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
}

/**
 * An anticipated action that may require confirmation
 */
export interface Anticipation {
  id: string;
  action: string;
  confidence: number; // 0-1
  risk: RiskLevel;
  subject: string; // Subject making the anticipation
  requires_confirmation: boolean;
}

/**
 * AnticipationEngine surfaces or queues anticipated actions
 * based on confidence and trust tier of the subject.
 */
export class AnticipationEngine {
  private authority: AuthorityRegistry;
  private surfaced: Anticipation[] = [];
  private queued: Anticipation[] = [];

  constructor(authority: AuthorityRegistry) {
    this.authority = authority;
  }

  /**
   * Process an anticipated action.
   * - High-confidence anticipations (>= 0.7) are surfaced
   * - Low-confidence anticipations (< 0.7) are queued
   * - TrustTier.Suggest causes requires_confirmation: true
   * - TrustTier.Auto with low/medium risk causes requires_confirmation: false
   * - TrustTier.Auto with high risk causes requires_confirmation: true
   */
  anticipate(anticipation: Anticipation): void {
    const tier = this.authority.getTier(anticipation.subject);

    // Determine if confirmation is required based on tier and risk
    let requiresConfirmation = false;

    if (tier === TrustTier.Suggest) {
      // Suggest tier always requires confirmation
      requiresConfirmation = true;
    } else if (tier === TrustTier.Auto) {
      // Auto tier: confirm only for high risk
      requiresConfirmation = anticipation.risk === RiskLevel.High;
    } else if (tier === TrustTier.Observe) {
      // Observe tier: confirm for medium and high risk
      requiresConfirmation =
        anticipation.risk === RiskLevel.Medium || anticipation.risk === RiskLevel.High;
    } else if (tier === TrustTier.Act) {
      // Act tier: no confirmation needed
      requiresConfirmation = false;
    }

    anticipation.requires_confirmation = requiresConfirmation;

    // Determine if surfaced or queued based on confidence
    if (anticipation.confidence >= 0.7) {
      this.surfaced.push(anticipation);
    } else {
      this.queued.push(anticipation);
    }
  }

  /**
   * Get surfaced (high-confidence) anticipations
   */
  getSurfaced(): Anticipation[] {
    return [...this.surfaced];
  }

  /**
   * Get queued (low-confidence) anticipations
   */
  getQueued(): Anticipation[] {
    return [...this.queued];
  }

  /**
   * Clear all anticipations
   */
  reset(): void {
    this.surfaced = [];
    this.queued = [];
  }
}

describe('AnticipationEngine', () => {
  let engine: AnticipationEngine;
  let authority: AuthorityRegistry;

  beforeEach(() => {
    authority = new AuthorityRegistry();
    engine = new AnticipationEngine(authority);
  });

  it('high-confidence anticipations appear in surfaced[], low-confidence in queued[]', () => {
    // Set subject to Suggest tier (any tier will work for this test)
    authority.setTier('agent-1', TrustTier.Suggest, { manual: true });

    const highConf: Anticipation = {
      id: 'high-1',
      action: 'deploy',
      confidence: 0.95,
      risk: RiskLevel.Low,
      subject: 'agent-1',
      requires_confirmation: false,
    };

    const lowConf: Anticipation = {
      id: 'low-1',
      action: 'debug',
      confidence: 0.5,
      risk: RiskLevel.Low,
      subject: 'agent-1',
      requires_confirmation: false,
    };

    engine.anticipate(highConf);
    engine.anticipate(lowConf);

    const surfaced = engine.getSurfaced();
    const queued = engine.getQueued();

    expect(surfaced.map((a) => a.id)).toContain('high-1');
    expect(queued.map((a) => a.id)).toContain('low-1');
  });

  it('TrustTier.Suggest subject causes requires_confirmation:true even for low-risk anticipations', () => {
    authority.setTier('agent-suggest', TrustTier.Suggest, { manual: true });

    const lowRisk: Anticipation = {
      id: 'suggest-low',
      action: 'log',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'agent-suggest',
      requires_confirmation: false,
    };

    engine.anticipate(lowRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(true);
  });

  it('TrustTier.Auto with low risk causes requires_confirmation:false', () => {
    authority.setTier('agent-auto', TrustTier.Auto, { manual: true });

    const lowRisk: Anticipation = {
      id: 'auto-low',
      action: 'read',
      confidence: 0.85,
      risk: RiskLevel.Low,
      subject: 'agent-auto',
      requires_confirmation: false,
    };

    engine.anticipate(lowRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(false);
  });

  it('TrustTier.Auto with medium risk causes requires_confirmation:false', () => {
    authority.setTier('agent-auto-med', TrustTier.Auto, { manual: true });

    const mediumRisk: Anticipation = {
      id: 'auto-med',
      action: 'update',
      confidence: 0.85,
      risk: RiskLevel.Medium,
      subject: 'agent-auto-med',
      requires_confirmation: false,
    };

    engine.anticipate(mediumRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(false);
  });

  it('TrustTier.Auto with high risk causes requires_confirmation:true', () => {
    authority.setTier('agent-auto-high', TrustTier.Auto, { manual: true });

    const highRisk: Anticipation = {
      id: 'auto-high',
      action: 'delete',
      confidence: 0.85,
      risk: RiskLevel.High,
      subject: 'agent-auto-high',
      requires_confirmation: false,
    };

    engine.anticipate(highRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(true);
  });

  it('TrustTier.Observe with low risk causes requires_confirmation:false', () => {
    authority.setTier('agent-observe', TrustTier.Observe, { manual: true });

    const lowRisk: Anticipation = {
      id: 'observe-low',
      action: 'scan',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'agent-observe',
      requires_confirmation: false,
    };

    engine.anticipate(lowRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(false);
  });

  it('TrustTier.Observe with medium risk causes requires_confirmation:true', () => {
    authority.setTier('agent-observe-med', TrustTier.Observe, { manual: true });

    const mediumRisk: Anticipation = {
      id: 'observe-med',
      action: 'modify',
      confidence: 0.8,
      risk: RiskLevel.Medium,
      subject: 'agent-observe-med',
      requires_confirmation: false,
    };

    engine.anticipate(mediumRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(true);
  });

  it('TrustTier.Act never requires confirmation regardless of risk', () => {
    authority.setTier('agent-act', TrustTier.Act, { manual: true });

    const highRisk: Anticipation = {
      id: 'act-high',
      action: 'destroy',
      confidence: 0.8,
      risk: RiskLevel.High,
      subject: 'agent-act',
      requires_confirmation: false,
    };

    engine.anticipate(highRisk);

    const surfaced = engine.getSurfaced();
    expect(surfaced[0].requires_confirmation).toBe(false);
  });

  it('default tier (Suggest) is used when subject tier is not set', () => {
    // Don't set a tier for 'unknown-agent' — should default to Suggest
    const anticipation: Anticipation = {
      id: 'default-tier',
      action: 'act',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'unknown-agent',
      requires_confirmation: false,
    };

    engine.anticipate(anticipation);

    const surfaced = engine.getSurfaced();
    // Suggest tier requires confirmation
    expect(surfaced[0].requires_confirmation).toBe(true);
  });

  it('reset clears all surfaced and queued anticipations', () => {
    authority.setTier('agent-x', TrustTier.Suggest, { manual: true });

    const anticipation: Anticipation = {
      id: 'test',
      action: 'test',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'agent-x',
      requires_confirmation: false,
    };

    engine.anticipate(anticipation);
    expect(engine.getSurfaced().length).toBe(1);

    engine.reset();
    expect(engine.getSurfaced().length).toBe(0);
    expect(engine.getQueued().length).toBe(0);
  });

  it('multiple anticipations from different subjects respect their own tiers', () => {
    authority.setTier('suggest-agent', TrustTier.Suggest, { manual: true });
    authority.setTier('auto-agent', TrustTier.Auto, { manual: true });

    const suggestAnticipation: Anticipation = {
      id: 'suggest-action',
      action: 'write',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'suggest-agent',
      requires_confirmation: false,
    };

    const autoAnticipation: Anticipation = {
      id: 'auto-action',
      action: 'write',
      confidence: 0.8,
      risk: RiskLevel.Low,
      subject: 'auto-agent',
      requires_confirmation: false,
    };

    engine.anticipate(suggestAnticipation);
    engine.anticipate(autoAnticipation);

    const surfaced = engine.getSurfaced();
    const suggestResult = surfaced.find((a) => a.id === 'suggest-action');
    const autoResult = surfaced.find((a) => a.id === 'auto-action');

    expect(suggestResult?.requires_confirmation).toBe(true);
    expect(autoResult?.requires_confirmation).toBe(false);
  });
});
