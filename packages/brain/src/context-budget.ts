/**
 * Context Budget Manager — Priority-aware context trimming with drop reporting
 * Fits items into a token budget by priority, trimming lowest-priority items
 * until the total fits. Dropped items are always reported explicitly.
 */

export interface ContextItem {
  id: string;
  priority: number;
  tokens: number;
  label?: string;
}

export interface BudgetResult {
  included: ContextItem[];
  dropped: ContextItem[];
  totalTokens: number;
  budgetTokens: number;
  utilization: number;
}

export class ContextBudgetManager {
  /**
   * Fit items into a token budget.
   * Items are sorted by priority (descending), then trimmed from lowest-priority
   * until the total fits within budgetTokens. Dropped items are always reported explicitly.
   *
   * @param items - Context items to fit, each with id, priority, and tokens
   * @param budgetTokens - Total token budget available
   * @returns BudgetResult with included/dropped items and utilization metrics
   */
  fit(items: ContextItem[], budgetTokens: number): BudgetResult {
    if (budgetTokens < 0) {
      throw new Error('Budget tokens must be non-negative');
    }

    if (items.length === 0) {
      return {
        included: [],
        dropped: [],
        totalTokens: 0,
        budgetTokens,
        utilization: 0,
      };
    }

    // Sort by priority descending (highest priority first)
    const sorted = [...items].sort((a, b) => b.priority - a.priority);

    const included: ContextItem[] = [];
    const dropped: ContextItem[] = [];
    let totalTokens = 0;

    // Add items until budget is exhausted
    for (const item of sorted) {
      if (totalTokens + item.tokens <= budgetTokens) {
        included.push(item);
        totalTokens += item.tokens;
      } else {
        dropped.push(item);
      }
    }

    const utilization = budgetTokens > 0 ? (totalTokens / budgetTokens) * 100 : 0;

    return {
      included,
      dropped,
      totalTokens,
      budgetTokens,
      utilization,
    };
  }

  /**
   * Calculate the impact of dropping lowest-priority items.
   * Returns information about what would be dropped at different priority thresholds.
   *
   * @param items - Context items to analyze
   * @param budgetTokens - Token budget to fit within
   * @returns Array of threshold impact objects showing (threshold, droppedCount, droppedTokens)
   */
  analyzeDropImpact(
    items: ContextItem[],
    budgetTokens: number,
  ): Array<{
    minPriority: number;
    droppedCount: number;
    droppedTokens: number;
  }> {
    if (items.length === 0) {
      return [];
    }

    const result = this.fit(items, budgetTokens);

    if (result.dropped.length === 0) {
      return [];
    }

    // Group dropped items by priority
    const byPriority = new Map<number, { count: number; tokens: number }>();

    for (const item of result.dropped) {
      const existing = byPriority.get(item.priority) || { count: 0, tokens: 0 };
      byPriority.set(item.priority, {
        count: existing.count + 1,
        tokens: existing.tokens + item.tokens,
      });
    }

    // Sort by priority descending and accumulate
    const sorted = Array.from(byPriority.entries())
      .sort((a, b) => b[0] - a[0])
      .map(([priority, stats]) => ({
        minPriority: priority,
        droppedCount: stats.count,
        droppedTokens: stats.tokens,
      }));

    return sorted;
  }
}
