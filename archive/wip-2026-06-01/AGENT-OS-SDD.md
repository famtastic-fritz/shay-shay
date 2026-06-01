# Shay-Shay Agent OS — Software Design Document v0.1
## Date: 2026-05-27
## Status: PLANNING — Research Phase Active

---

## 1. VISION STATEMENT

Build a modular Agent Operating System where:
- Shay is ambient, persistent, and context-aware
- Multiple specialized agents run in parallel under orchestration
- Research is the foundation of every decision
- Proofs-of-concept render inline without leaving the workspace
- A configurable trust mode enables autonomous action (spending, deploying, communicating)
- Memory spans sessions, models, and studios (Site Studio, Media Studio)
- Jailbroken brains are available as switchable personas
- All capabilities are assessable, benchmarkable, and improvable via a learning loop

---

## 2. ARCHITECTURE PRINCIPLES

1. **Kernel-first, modular by design** — Core orchestrator + plug-in agents
2. **Parallel execution by default** — Agents work like threads, not silos
3. **Research-before-build** — Every feature is backed by discovery and citation
4. **Cross-studio bridge** — Shay Desktop orchestrates Site Studio, Media Studio, Data Center
5. **CLI-first, desktop is skin** — Electron desktop renders; CLI does the work
6. **Trust mode** — Configurable autonomy levels for money, accounts, deploy, communication, code
7. **Learning loop** — Every session extracts lessons → skills + memory + research center

---

## 3. SYSTEM COMPONENTS

### 3.1 CORE KERNEL (Priority 1)
| Component | Purpose | Status |
|-----------|---------|--------|
| **Orchestrator** | Route tasks to agents, manage queues, handle conflicts | NOT BUILT |
| **Agent Registry** | Catalog available agents, their capabilities, current load | NOT BUILT |
| **Memory Engine** | Hybrid: SQLite/graph for retrieval + Obsidian for readable handoffs | NOT BUILT |
| **Session Manager** | Save/load/branch session states, visualize timelines | PARTIAL (checkpoint exists) |
| **Trust Manager** | Configurable approval boundaries per action type | NOT BUILT |

### 3.2 PRIORITY THREE (Dashboard, Jailbreak, Memory)
| Component | Purpose | Status |
|-----------|---------|--------|
| **Dashboard/Workspace** | Tab-based main area + sidebar (Julian Goldie pattern) | NOT BUILT |
| **Brain Switcher** | Manual model/persona switch mid-conversation | NOT BUILT |
| **Jailbreak Sandbox** | Test compliance/refusal across uncensored models | NOT BUILT |
| **Memory Visualizer** | Timeline, branching sessions, knowledge graph | NOT BUILT |

### 3.3 SUPPORTING SYSTEMS
| Component | Purpose | Status |
|-----------|---------|--------|
| **Research Center** | Idea DB, search, citation tracking, research agents | NOT BUILT |
| **Benchmark Arena** | Compare model outputs side-by-side (images, voice, code) | NOT BUILT |
| **Proof Viewer** | Inline HTML preview without leaving desktop | NOT BUILT |
| **Agent Builder** | UI for creating/configuring agents, capturing recipes | NOT BUILT |
| **API/Key Manager** | Rotation, signup automation, payment handling | NOT BUILT |
| **Debate Arena** | Multi-model argumentation on decisions | NOT BUILT |
| **Ambient Reporter** | Background context snapshots → Obsidian | WORKING (cron active) |
| **Context Daemon** | Desktop state monitoring | WORKING |

### 3.4 STUDIO BRIDGES
| Bridge | Function |
|--------|----------|
| **Site Studio** | Send build requests, receive deployed URLs, preview sites inline |
| **Media Studio** | Generate assets, view galleries inline, send to Site Studio |
| **Data Center** | Collect post-eval data, improve skills/processes |

---

## 4. RESEARCH DEEP DIVES (Active)

### 4.1 Hugging Face Deep Dive
**Goal:** Find uncensored models and agent frameworks
**Hint model:** TrevorJS/gemma-4-uncensored collections
**Search scope:**
- Uncensored fine-tunes (NSFW, unfiltered, no-refusal)
- Agent-optimized models (tool use, long context, reasoning)
- Quantization formats (GGUF, GPTQ, AWQ) for local inference
- Hardware requirements and benchmarks
- Existing agent/swarm collections

### 4.2 Kimi Swarm Architecture Deep Dive  
**Goal:** Reverse-engineer or find open-source equivalents
**Search scope:**
- "Kimi agent swarm" implementations on GitHub
- End-to-end pipelines: research → code → test → review → deploy
- Single-prompt-to-full-application patterns
- Quality control and error recovery in multi-agent systems
- How they achieve minute-level vs hour-level builds

### 4.3 Agent Builder Interfaces Deep Dive
**Goal:** Design our agent creation UX
**Search scope:**
- OpenAI Codex agent/prompt configuration system
- Claude Code slash commands and custom agent patterns
- Open-source agent builder/constructor/factory projects
- Kimi/Moonshot AI agent creation patterns
- Recipe capture and reuse systems

---

## 5. EXECUTION ORCHESTRATION STRUCTURE

### Phase 0: Foundation (Current)
- [ ] Complete all 3 research deep dives
- [ ] Document findings in Research Center
- [ ] Select base models for jailbreak personas
- [ ] Design Agent Builder interface spec
- [ ] Define agent communication protocol (MCP? Custom?)

### Phase 1: Kernel Build
- [ ] Build Orchestrator with parallel agent spawning
- [ ] Build Agent Registry with capability metadata
- [ ] Build Memory Engine (SQLite + Obsidian hybrid)
- [ ] Build Trust Manager with configurable levels
- [ ] Build inline Proof Viewer (iframe renderer)

### Phase 2: Priority Three
- [ ] Build Dashboard workspace (tab system)
- [ ] Build Brain Switcher with persona registry
- [ ] Build Jailbreak Sandbox (model compliance testing)
- [ ] Build Memory Visualizer

### Phase 3: Supporting Systems
- [ ] Build Research Center with idea DB
- [ ] Build Benchmark Arena
- [ ] Build Agent Builder UI
- [ ] Build API/Key Manager automation
- [ ] Build Debate Arena

### Phase 4: Studio Integration
- [ ] Wire Site Studio bridge (inline preview)
- [ ] Wire Media Studio bridge (logo-lab, asset galleries)
- [ ] Wire Data Center (post-eval learning)

### Phase 5: Autonomy & Scale
- [ ] Deploy trust mode for autonomous actions
- [ ] Phone app interface
- [ ] Avatar/voice/body virtual presence
- [ ] Forex/stock trader agent as validation test

---

## 6. AGENT SWARM DESIGN

### Single-Prompt Pipeline (Inspired by Kimi)
```
User prompt → Orchestrator
  
  ├→ Research Agent: discovers solutions, competitors
  ├→ Architecture Agent: designs system/components
  ├→ Builder Agent(s): writes code in parallel
  ├→ Test Agent: validates correctness
  ├→ Review Agent: quality gates
  └→ Deploy Agent: ships + monitors

  ↓
Orchestrator aggregates → Presents to user with diff + proof
```

### Key Innovations Needed
1. **Fast feedback loops** — Agents don't wait for each other serially
2. **Error recovery** — If builder fails, auto-retry with architecture fix
3. **Skill extraction** — Successful recipes become reusable templates
4. **Human checkpoint** — User can pause/override at any stage

---

## 7. TRUST MODE LEVELS

| Level | Money | Accounts | Deploy | Communicate | Code |
|-------|-------|----------|--------|-------------|------|
| 0 - Locked | Ask always | Ask always | Ask always | Ask always | Ask always |  
| 1 - Assisted | Under $10 | Major only | Staging only | Draft only | PR review |
| 2 - Trusted | Under $100 | Auto-create | Auto-deploy | Auto-send | Auto-commit |
| 3 - Autonomous | Any amount | Auto-create | Auto-deploy | Auto-send | Auto-merge |

---

## 8. KNOWN GAPS (Honest)

1. No working orchestrator — agents don't yet spawn and coordinate automatically
2. No inline proof viewer — still opening browser for HTML outputs
3. No research center — ideas scattered across Obsidian files
4. No agent builder UI — currently CLI-only agent config
5. No trust mode implementation — all actions require manual approval
6. Desktop app has naming/port conflicts (hermes/shay duality)
7. No model benchmarking sandbox
8. Background job tracking is fragile (polling loops crash)

---

## 9. NEXT ACTIONS

1. **Research agents return findings** ← WE ARE HERE
2. Select base models and frameworks from research
3. Write agent communication protocol spec
4. Build Phase 0: Kernel scaffolding
5. Test with forex/stock trader as validation

---

*This SDD is a living document. Research findings will append as sections 10+.*
