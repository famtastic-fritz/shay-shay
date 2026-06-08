/**
 * @shay/brain
 * Brain Router and Anticipation Engine
 * Reasoning chain orchestration and proactive cross-cutting
 */

export {
  BrainRouter,
  Lane,
  LaneKind,
  CapState,
  BrainRequest,
  BrainResponse,
  createMockLane,
} from './router.js';

export {
  ResumableRunner,
  RunStep,
  CheckpointRecord,
  StallPolicy,
  BrainCallFn,
} from './resume.js';

export {
  ContextBudgetManager,
  ContextItem,
  BudgetResult,
} from './context-budget.js';

export {
  AnticipationEngine,
  Anticipation,
  TurnOutcome,
  AnticipationResult,
} from './anticipation.js';
