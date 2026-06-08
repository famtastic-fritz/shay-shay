import { describe, it, expect, vi } from 'vitest';
import { AuthorityRegistry, TrustTier } from '../../core/src/authority.js';
import { EventBus } from '../../core/src/event-bus.js';

describe('AuthorityRegistry', () => {
  it('getTier() on unknown subject returns TrustTier.Suggest (1)', () => {
    const registry = new AuthorityRegistry();
    const tier = registry.getTier('unknown-subject');

    expect(tier).toBe(TrustTier.Suggest);
    expect(tier).toBe(1);
  });

  it('setTier() with manual:true succeeds and getTier() reflects new value', () => {
    const registry = new AuthorityRegistry();

    registry.setTier('test-subject', TrustTier.Observe, { manual: true });
    const tier = registry.getTier('test-subject');

    expect(tier).toBe(TrustTier.Observe);
    expect(tier).toBe(0);
  });

  it('setTier() with manual:false throws an Error', () => {
    const registry = new AuthorityRegistry();

    expect(() => {
      registry.setTier('test-subject', TrustTier.Confirm, { manual: false });
    }).toThrow();
  });

  it('setTier() with opts omitted entirely throws', () => {
    const registry = new AuthorityRegistry();

    expect(() => {
      registry.setTier('test-subject', TrustTier.Confirm, undefined as any);
    }).toThrow();
  });

  it('can(subject, TrustTier.Observe) is true for default tier (Observe < Suggest)', () => {
    const registry = new AuthorityRegistry();
    const canObserve = registry.can('any-subject', TrustTier.Observe);

    expect(canObserve).toBe(true);
  });

  it('can(subject, TrustTier.Auto) is false for default tier (Auto > Suggest)', () => {
    const registry = new AuthorityRegistry();
    const canAuto = registry.can('any-subject', TrustTier.Auto);

    expect(canAuto).toBe(false);
  });

  it('promote() with manual:true sets tier', () => {
    const registry = new AuthorityRegistry();

    registry.promote('subject', TrustTier.Confirm, { manual: true });
    const tier = registry.getTier('subject');

    expect(tier).toBe(TrustTier.Confirm);
  });

  it('promote() with manual:false throws', () => {
    const registry = new AuthorityRegistry();

    expect(() => {
      registry.promote('subject', TrustTier.Confirm, { manual: false });
    }).toThrow();
  });

  it('When EventBus is injected, a "authority:tier-changed" event is emitted on successful setTier', () => {
    const eventBusMock = {
      emit: vi.fn(),
      subscribe: vi.fn(),
    } as unknown as EventBus;

    const registry = new AuthorityRegistry(eventBusMock);

    registry.setTier('test-subject', TrustTier.Observe, { manual: true });

    expect(eventBusMock.emit).toHaveBeenCalled();
    const callArgs = (eventBusMock.emit as ReturnType<typeof vi.fn>).mock.calls[0];
    const emittedEvent = callArgs[0];

    expect((emittedEvent as any).type).toBe('authority:tier-changed');
    expect((emittedEvent as any).payload.subject).toBe('test-subject');
    expect((emittedEvent as any).payload.tier).toBe(TrustTier.Observe);
  });

  it('promote() also emits authority:tier-changed when EventBus is present', () => {
    const eventBusMock = {
      emit: vi.fn(),
      subscribe: vi.fn(),
    } as unknown as EventBus;

    const registry = new AuthorityRegistry(eventBusMock);

    registry.promote('subject', TrustTier.Auto, { manual: true });

    expect(eventBusMock.emit).toHaveBeenCalled();
    const callArgs = (eventBusMock.emit as ReturnType<typeof vi.fn>).mock.calls[0];
    const emittedEvent = callArgs[0];

    expect((emittedEvent as any).type).toBe('authority:tier-changed');
    expect((emittedEvent as any).payload.subject).toBe('subject');
    expect((emittedEvent as any).payload.tier).toBe(TrustTier.Auto);
  });

  it('can(subject, TrustTier.Suggest) is true for default tier', () => {
    const registry = new AuthorityRegistry();
    const canSuggest = registry.can('any-subject', TrustTier.Suggest);

    expect(canSuggest).toBe(true);
  });
});
