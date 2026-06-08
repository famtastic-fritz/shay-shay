# Phase Workflow Template

A reusable recipe for all future phase builders. Every phase follows this structure to ensure consistency, catch errors early, and deliver testable, verifiable results.

---

## Phase {{PHASE_NUMBER}}: {{SUBSYSTEM}}

**Goal:** {{GOAL_STATEMENT}}

**Input State:** What exists before this phase starts (e.g., "Phase 0 complete, @shay/doctor gate passing").

**Output State:** What must exist when this phase ships (e.g., "Package @shay/{{SUBSYSTEM}} published with all interfaces stable, gate passing, LOCKED.json updated").

---

## 1. Decompose

Break the phase into **file groups**. Each group is a unit of work that can be built, tested, and verified independently before moving to the next.

Example template for a typical package phase:

| Group | Files | Dependencies | Owner |
|-------|-------|--------------|-------|
| Manifest | `packages/{{SUBSYSTEM}}/package.json`, `tsconfig.json` | None | Phase lead |
| Types & Interfaces | `packages/{{SUBSYSTEM}}/src/types.ts` | Manifest | Core architect |
| Core Implementation | `packages/{{SUBSYSTEM}}/src/index.ts`, supporting modules | Types | Subsystem builder |
| Unit Tests | `packages/{{SUBSYSTEM}}/src/__tests__/*.test.ts` | Core Implementation | QA / Builder |
| Export & Build | Update root `package.json` workspaces, run `npm install` | All groups above | Build automation |

**Identify collision domains:**
- Manifest files: `package.json`, `tsconfig.json` (only one owner per package).
- Root config: `shay.config.yaml`, `schemas/`, root `package.json` workspaces.
- Interfaces: `src/types.ts` (owned by first group to write it; others extend via module augmentation or new files).

**List inter-group dependencies:**
- Group A must finish before Group B starts if A produces files B imports.
- Document the blocking dependency and the trigger (e.g., "Types group completes → Core Implementation can begin").

---

## 2. Build

Follow this process for each file group:

### 2.1 Write Files

Write all files in the group in a single pass or batch. Do not interleave with other groups.

Example for Types group:
```typescript
// packages/core/src/types.ts
export interface ConfigRegistry {
  get(key: string): unknown;
  set(key: string, value: unknown): void;
}

export interface EventBus {
  emit(event: string, payload: unknown): void;
  on(event: string, handler: (payload: unknown) => void): void;
}
```

### 2.2 Type-Check Early

After writing each group, run:

```bash
cd /Users/famtasticfritz/famtastic/shay-shay-build
npx tsc --noEmit
```

If there are errors, fix them immediately. Do not move to the next group with type errors.

Example error and fix:
```
error TS2339: Property 'emit' does not exist on type 'EventBus'
```
→ Add the property to the interface or correct the implementation.

### 2.3 Minimal Stubs

If a group depends on another subsystem that is not yet built:
- Create a stub in `packages/<dependency>/src/index.ts` with minimal exports.
- Document it in the phase plan as "stub provided for {{SUBSYSTEM}} to complete without waiting".
- Example: EventBus is a stub if Router (Group 3) needs it but hasn't shipped yet.

### 2.4 Document As You Build

Add comments to clarify intent and integration points:

```typescript
// EventBus is the system-wide event router.
// Subsystems emit events; listeners subscribe via on().
// See SITE-LEARNINGS.md for the full event taxonomy.
export interface EventBus {
  emit(event: string, payload: unknown): void;
  on(event: string, handler: (payload: unknown) => void): void;
}
```

---

## 3. Verify

### 3.1 Unit Tests (if applicable)

If the group includes tests, run them:

```bash
cd /Users/famtasticfritz/famtastic/shay-shay-build
npm test -- packages/{{SUBSYSTEM}}
```

All tests must pass. If a test fails, fix the code, not the test.

### 3.2 Run the Doctor's Gate

At the end of the phase, run the full gate:

```bash
cd /Users/famtasticfritz/famtastic/shay-shay-build
node -e 'import("@shay/doctor").then(m => m.runGate(".")).then(result => { console.log(JSON.stringify(result, null, 2)); process.exit(result.pass ? 0 : 1); })'
```

Expected output:
```json
{
  "pass": true,
  "subsystems": {
    "core": { "phase": 1, "status": "healthy" },
    "{{SUBSYSTEM}}": { "phase": {{PHASE_NUMBER}}, "status": "healthy" }
  },
  "timestamp": "2026-06-08T12:34:56.789Z"
}
```

If `pass` is `false`, the output will show which checks failed. Fix them before proceeding.

### 3.3 Manual Spot Checks

For critical subsystems (Core, Doctor), manually verify key behaviors:

```bash
cd /Users/famtastic/shay-shay-build

# Example: Verify ConfigRegistry reads and writes
node -e '
import("@shay/core").then(m => {
  const reg = new m.ConfigRegistry();
  reg.set("test.key", "value");
  console.log("Value:", reg.get("test.key"));
  process.exit(reg.get("test.key") === "value" ? 0 : 1);
})
'
```

---

## 4. Stamp

Once the phase verifies successfully, record it in LOCKED.json:

```bash
node tools/provenance.mjs {{SUBSYSTEM}} {{PHASE_NUMBER}}
```

Example:
```bash
node tools/provenance.mjs core 1
```

Output:
```
Stamped core phase 1 at 2026-06-08T12:34:56.789Z
Checksum: a1b2c3d4e5f6...
```

This records that `@shay/{{SUBSYSTEM}}` has shipped Phase {{PHASE_NUMBER}} with a verifiable checksum.

---

## 5. Commit

Create a conventional commit with all phase changes:

```bash
git add packages/{{SUBSYSTEM}} docs/ LOCKED.json

git commit -m "feat({{SUBSYSTEM}}): {{GOAL_STATEMENT}}"
```

**Rules:**
- No `--no-verify` flag; let pre-commit hooks run.
- No `--amend`; create a new commit for each logical unit.
- No AI references anywhere in the message or body.
- Use imperative present tense ("add", "fix", not "added", "fixed").

Example commit for Phase 1 (Core):
```
git commit -m "feat(core): implement config registry, event bus, and credential vault with gate"
```

---

## Phase Checklist

Use this checklist to verify a phase is complete before shipping:

- [ ] All file groups identified and dependencies mapped
- [ ] All files written (no placeholders or TODOs left behind)
- [ ] `tsc --noEmit` passes with no errors
- [ ] Unit tests pass (if applicable)
- [ ] Doctor's gate passes with `pass: true`
- [ ] Manual spot checks pass
- [ ] `LOCKED.json` stamped with correct phase and checksum
- [ ] Conventional commit created (no `--no-verify`, no AI references)
- [ ] Git log shows the new commit
- [ ] SITE-LEARNINGS.md updated (if meaningful discoveries)

---

## Template Variables

- `{{PHASE_NUMBER}}` — The phase number (0, 1, 2, etc.)
- `{{SUBSYSTEM}}` — The subsystem being built (e.g., "core", "doctor", "memory")
- `{{GOAL_STATEMENT}}` — A one-sentence goal (e.g., "Implement config registry and event bus")
- `{{FILES_CHANGED}}` — Count of files added/modified in this phase

---

## Notes

- **Parallelization within a phase:** Groups with no dependencies can be built in parallel (if using multiple builders), but each group must complete type-checking before moving to the next group that depends on it.
- **Rollback:** If a phase fails the gate after commit, use `git revert` to undo it and fix the issues.
- **Stub lifecycle:** Stubs are replaced when the real implementation ships. Document which stubs are active in the phase plan.
- **Documentation:** Phases that add new packages, endpoints, or config keys require updates to SITE-LEARNINGS.md.

---

Last updated: 2026-06-08
