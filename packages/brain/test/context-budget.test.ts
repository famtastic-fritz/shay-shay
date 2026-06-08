import { describe, it, expect, beforeEach } from 'vitest';

/**
 * Priority level for an item in context budget
 */
export enum ItemPriority {
  Critical = 0,
  High = 1,
  Medium = 2,
  Low = 3,
}

/**
 * An item that consumes context tokens
 */
export interface ContextItem {
  id: string;
  tokens: number;
  priority: ItemPriority;
  content: string;
}

/**
 * Result of budget allocation
 */
export interface BudgetAllocation {
  included: ContextItem[];
  dropped: ContextItem[];
}

/**
 * ContextBudgetManager allocates items within a token budget,
 * dropping lowest-priority items first when necessary.
 */
export class ContextBudgetManager {
  private budget: number;

  constructor(budget: number) {
    this.budget = budget;
  }

  /**
   * Allocate items within the budget.
   * Returns included items and dropped items.
   * Lowest-priority (highest number) items are dropped first.
   */
  allocate(items: ContextItem[]): BudgetAllocation {
    if (items.length === 0) {
      return { included: [], dropped: [] };
    }

    // Calculate total tokens needed
    const totalTokens = items.reduce((sum, item) => sum + item.tokens, 0);

    // If everything fits, return all items
    if (totalTokens <= this.budget) {
      return { included: items, dropped: [] };
    }

    // Sort items by priority (critical first) and then by token count (ascending)
    const sorted = [...items].sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority; // Lower number = higher priority
      }
      return a.tokens - b.tokens; // Smaller items first
    });

    const included: ContextItem[] = [];
    let usedTokens = 0;

    // Add items in priority order until budget is exhausted
    for (const item of sorted) {
      if (usedTokens + item.tokens <= this.budget) {
        included.push(item);
        usedTokens += item.tokens;
      }
    }

    // Dropped items are those not included
    const droppedSet = new Set(items);
    included.forEach((item) => droppedSet.delete(item));
    const dropped = Array.from(droppedSet);

    return { included, dropped };
  }
}

describe('ContextBudgetManager', () => {
  let manager: ContextBudgetManager;

  beforeEach(() => {
    manager = new ContextBudgetManager(1000);
  });

  it('items fitting within budget are all included', () => {
    const items: ContextItem[] = [
      {
        id: 'item1',
        tokens: 300,
        priority: ItemPriority.High,
        content: 'content1',
      },
      {
        id: 'item2',
        tokens: 300,
        priority: ItemPriority.Medium,
        content: 'content2',
      },
      {
        id: 'item3',
        tokens: 300,
        priority: ItemPriority.Low,
        content: 'content3',
      },
    ];

    const result = manager.allocate(items);

    expect(result.included).toHaveLength(3);
    expect(result.dropped).toHaveLength(0);
  });

  it('lowest-priority items are dropped first when over budget', () => {
    const items: ContextItem[] = [
      {
        id: 'critical',
        tokens: 400,
        priority: ItemPriority.Critical,
        content: 'critical content',
      },
      {
        id: 'high',
        tokens: 300,
        priority: ItemPriority.High,
        content: 'high content',
      },
      {
        id: 'medium',
        tokens: 200,
        priority: ItemPriority.Medium,
        content: 'medium content',
      },
      {
        id: 'low',
        tokens: 200,
        priority: ItemPriority.Low,
        content: 'low content',
      },
    ];

    const result = manager.allocate(items);

    // Should include critical (400) + high (300) + medium (200) = 900 tokens, drop low (200)
    expect(result.included.map((item) => item.id)).toContain('critical');
    expect(result.included.map((item) => item.id)).toContain('high');
    expect(result.included.map((item) => item.id)).toContain('medium');
    expect(result.included.map((item) => item.id)).not.toContain('low');
    expect(result.dropped.map((item) => item.id)).toContain('low');
    expect(result.dropped).toHaveLength(1);
  });

  it('dropped array is always populated with the items that were trimmed', () => {
    const items: ContextItem[] = [
      {
        id: 'item1',
        tokens: 600,
        priority: ItemPriority.High,
        content: 'content1',
      },
      {
        id: 'item2',
        tokens: 600,
        priority: ItemPriority.Low,
        content: 'content2',
      },
    ];

    const result = manager.allocate(items);

    expect(result.dropped.length).toBeGreaterThan(0);
    expect(result.dropped.some((item) => item.id === 'item2')).toBe(true);
  });

  it('exact boundary (sum == budget) passes with nothing dropped', () => {
    const items: ContextItem[] = [
      {
        id: 'item1',
        tokens: 333,
        priority: ItemPriority.High,
        content: 'content1',
      },
      {
        id: 'item2',
        tokens: 333,
        priority: ItemPriority.Medium,
        content: 'content2',
      },
      {
        id: 'item3',
        tokens: 334,
        priority: ItemPriority.Low,
        content: 'content3',
      },
    ];

    const result = manager.allocate(items);

    expect(result.included).toHaveLength(3);
    expect(result.dropped).toHaveLength(0);
  });

  it('empty items array returns empty included and dropped', () => {
    const result = manager.allocate([]);

    expect(result.included).toEqual([]);
    expect(result.dropped).toEqual([]);
  });

  it('single item over budget is dropped', () => {
    const items: ContextItem[] = [
      {
        id: 'oversized',
        tokens: 1500,
        priority: ItemPriority.Low,
        content: 'too big',
      },
    ];

    const result = manager.allocate(items);

    expect(result.included).toHaveLength(0);
    expect(result.dropped).toHaveLength(1);
    expect(result.dropped[0].id).toBe('oversized');
  });

  it('items with same priority are sorted by token count', () => {
    const manager2 = new ContextBudgetManager(400);

    const items: ContextItem[] = [
      {
        id: 'large',
        tokens: 300,
        priority: ItemPriority.Medium,
        content: 'content',
      },
      {
        id: 'small',
        tokens: 100,
        priority: ItemPriority.Medium,
        content: 'content',
      },
      {
        id: 'medium',
        tokens: 200,
        priority: ItemPriority.Medium,
        content: 'content',
      },
    ];

    const result = manager2.allocate(items);

    // Should include small (100) + medium (200) = 300, drop large (300)
    expect(result.included.map((item) => item.id)).toContain('small');
    expect(result.included.map((item) => item.id)).toContain('medium');
    expect(result.included.map((item) => item.id)).not.toContain('large');
  });
});
