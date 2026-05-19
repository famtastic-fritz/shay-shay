# 2026-05-19 — Media Studio Solutions Backlog (Hermes pass)

> **Snapshot from:** `~/famtastic/media-studio/SOLUTIONS-BACKLOG.md`
> (canonical source — that file gets updated as the backlog is worked).
>
> Filed in `shay-shay/docs/plans/` so Shay has the Media Studio build
> plan in its knowledge base. The Hermes pattern itself — observe →
> identify gaps → propose solutions → schedule — is a workflow Shay can
> apply to any post-experiment review.
>
> **Related context:**
> - Brand-mark manifesto: `~/famtastic/brand/FAMTASTIC-BRAND-MARK.md`
> - Remotion engine (Phase 1 done): `~/famtastic/remotion/`
> - Recipe catalog: `~/famtastic/remotion/RECIPES.md`
> - SITE-LEARNINGS entry: top of `~/famtastic/SITE-LEARNINGS.md`
> - Standing rule (memory): use muapi recipe skills, not primitives,
>   for brand/media work
> - Verified muapi model catalog + gotchas: `~/famtastic/.wolf/cerebrum.md`

---

# Media Studio — Solutions Backlog (Hermes Pass)

> Every gap identified during the **2026-05-19 muapi recipe rebuild
> experiment** mapped to a concrete proposed solution, sized, and ready to
> work through. This is the build queue for the Media Studio wrapper.
>
> Generated post-experiment per the "Hermes review" pattern: observe →
> identify gaps → propose solutions → schedule.

---

## Severity scale
- **P0** — blocks core function; the wrapper can't ship without it
- **P1** — meaningfully degrades quality/reliability
- **P2** — quality-of-life, optimization, nice-to-have

---

## Section A — muapi recipe limitations (external constraints)

### GAP A1 — Recipe specs reference model aliases not in muapi catalog
**Severity:** P0
**Observed:** `ideogram-v3-t2i`, `flux-2-pro`, `nano-banana-pro`, `nano-banana-2`, `nano-banana-2-edit`, `bytedance-seedream-v4.5`, `gpt-image-2-text-to-image`, `veo3.1-fast-image-to-video` are referenced by muapi recipe skills but are NOT in `muapi models list`.
**Proposed solution:** A model-alias map maintained in the wrapper.
- File: `media-studio/lib/model-aliases.json`
- Schema: `{ "<recipe-model>": ["<primary>", "<fallback1>", "<fallback2>"] }`
- Wrapper translates aliases at call time, walks the list until one succeeds.
- Map seeded with today's known substitutions:
  ```json
  {
    "ideogram-v3-t2i":         ["gpt4o", "hidream-full", "flux-dev"],
    "flux-2-pro":              ["flux-dev", "hidream-full", "flux-kontext-pro"],
    "nano-banana-pro":         ["gpt4o", "flux-kontext-max", "flux-dev"],
    "nano-banana-2":           ["flux-dev", "gpt4o"],
    "nano-banana-2-edit":      ["flux-kontext-max", "flux-kontext-pro"],
    "bytedance-seedream-v4.5": ["gpt4o", "flux-dev"],
    "gpt-image-2-text-to-image": ["gpt4o"],
    "veo3.1-fast-image-to-video": ["wan2.2", "wan2.1"]
  }
  ```
- Cron job (weekly): re-run `muapi models list`, diff against the alias map, alert when new official models appear so we can update mappings.
**Affected components:** wrapper core
**Estimated effort:** 2 hours
**Verification:** unit test — feed each recipe-model alias to the wrapper, assert at least one mapped model resolves to a successful generation.

---

### GAP A2 — Some catalog models return "Not Found" on this account
**Severity:** P0
**Observed:** `midjourney`, `seedream`, `kling-pro`, `seedance-pro` all returned `{"detail":"Not Found"}` despite being listed in `muapi models list`. Possibly account-tier restrictions or partner-model availability.
**Proposed solution:** Per-model health-check + auto-fallback.
- Wrapper maintains `media-studio/lib/model-health.json` (writeable cache, refreshed weekly via lightweight dry-run probe).
- On `Not Found` at runtime, mark the model as unavailable, log the event, retry next in fallback chain.
- Send the model name + timestamp + error to a `model-health-events.log` so we have evidence to provide muapi support.
**Affected components:** wrapper core
**Estimated effort:** 2-3 hours
**Verification:** integration test — request a known-broken model, assert wrapper falls through to a working one and logs the failure.

---

### GAP A3 — veo3-fast CLI/API param mismatch
**Severity:** P1
**Observed:** `muapi video from-image --model veo3-fast` sends `image_url`, API rejects with "field required: images_list".
**Proposed solutions (pick one):**
- **Option A (preferred):** File a bug with muapi via their support channel; track upstream fix.
- **Option B (immediate):** Bypass the CLI for veo3-fast — wrapper calls the muapi API directly via fetch/curl with the correct payload shape.
- **Option C (fallback):** Mark `veo3-fast` for `from-image` as broken in `model-health.json`; auto-substitute `wan2.2`.
**Affected components:** wrapper's image-to-video path
**Estimated effort:** Option A: 0 (just file ticket). Option B: 1 hour. Option C: covered by GAP A2.
**Verification:** end-to-end test — request a veo3-fast i2v generation, expect either success or seamless fallback to wan2.2.

---

### GAP A4 — Multi-segment brand names render unreliably in generated logos
**Severity:** P0 (this was the most painful failure mode of the experiment)
**Observed:** Brand names like "FAMtastic" (FAM + tastic) come back as "AMtastic", "Famino", "TaSTIC", or with merged/dropped characters in logo outputs from gpt4o, flux-dev, hidream-full.
**Proposed solution:** **Two-stage logo composition pattern.**
- **Stage 1:** Generate the logo's visual elements WITHOUT brand-name text — burst, marks, ornamental geometry, color treatment. Models render visual structure reliably.
- **Stage 2:** Composite the brand-name text on top via Remotion (`@famtastic/remotion`) or PIL. We have 100% spelling control here, perfect typography, and brand-locked font choices.
- The wrapper's logo pipeline is: prompt → muapi (visuals only) → Remotion composite (visuals + clean text) → final logo.
- Bonus: this naturally supports multi-language brand variants — same visual, swap the text layer.
**Affected components:** wrapper logo pipeline; `@famtastic/remotion` composition library
**Estimated effort:** 4-6 hours (split between wrapper logic + a new `BrandedLogoComposite` Remotion composition)
**Verification:** OCR check — every wrapper-produced logo passes Tesseract OCR with the exact brand name string, no misspellings.

---

### GAP A5 — flux-kontext-max edit drifts beyond instructions
**Severity:** P1
**Observed:** Asked for "add 3D depth, preserve composition." Got a beautiful but DIFFERENT composition (circular medallion crop where source was rectangular FAM + tastic banner). Lost "tastic" entirely.
**Proposed solution:** **Composition-preservation guard.**
- Capture the source image's content bounding-box, aspect ratio, dominant edge structure (Canny edge map).
- After flux-kontext-max returns the edit, compute SSIM (structural similarity index) vs the source.
- If SSIM < 0.65 (or another tuned threshold), reject the edit and retry with reinforced prompt OR fall back to a different edit model.
- Also: explicitly tag prompts that NEED preservation vs. allow reinterpretation. Some "make it 3D" prompts genuinely benefit from creative drift; some "fix this one thing" prompts don't.
**Affected components:** wrapper's image-edit path
**Estimated effort:** 2-3 hours (SSIM library is one-liner; tuning threshold takes the time)
**Verification:** test set — 10 known image-edit prompts; preservation-tagged ones must maintain SSIM > 0.65; non-tagged are unconstrained.

---

### GAP A6 — muapi/Remotion skill CLIs are stubbornly interactive
**Severity:** P2
**Observed:** `npx remotion skills add --yes --global` still prompted for a 23-agent picker. No flag to bypass.
**Proposed solution:** Document the workaround pattern, codify it.
- Pattern: `git clone <skill-source-repo> /tmp/<name> && cp -r /tmp/<name>/skills/<skill> ~/<target>/.claude/skills/`
- Wrapper provides a `media-studio/scripts/install-skill.sh <skill-name>` that automates this for both muapi recipe skills and other tool skills.
- For genuinely interactive prompts that can't be bypassed: spawn the CLI with `expect`-style scripted answers.
**Affected components:** wrapper's onboarding scripts
**Estimated effort:** 1 hour
**Verification:** running the install script for any known skill completes without human input.

---

## Section B — Wrapper requirements (the Media Studio orchestration layer)

### REQ B1 — Model-fallback chain (orchestration core)
**Severity:** P0
**Description:** Every muapi recipe call goes through the wrapper, which:
1. Reads recipe spec to extract model name(s).
2. Maps model name through alias map (GAP A1).
3. For each model in the fallback chain, attempts the call.
4. On `Not Found` / error, marks model + retries next.
5. Returns first successful generation, or `AllModelsFailed` if exhausted.
**Affected components:** wrapper core (`lib/muapi-call.ts`)
**Estimated effort:** 2 hours
**Verification:** unit test with mocked muapi returning Not Found for first N models in a chain.

---

### REQ B2 — OCR validation gate (text-output reliability)
**Severity:** P0
**Description:** After ANY recipe that includes brand-name text in the output (logos, mockups, design-guide pages):
1. Wrapper runs Tesseract OCR on the output image.
2. Asserts the expected brand name string is present (case-insensitive, allowing minor punctuation variance).
3. On fail, retries up to N times with reinforced prompt (`"the EXACT text 'FAMtastic' must appear, spelled F-A-M-t-a-s-t-i-c"`).
4. If still failing after retries, falls back to the GAP A4 two-stage pattern (generate visual, composite text).
**Affected components:** wrapper post-generation pipeline
**Estimated effort:** 3 hours (Tesseract install + retry logic + thresholds)
**Verification:** test 20 logo generations across recipes; OCR pass rate > 95%.

---

### REQ B3 — Composition-preservation guard
Covered by GAP A5 solution.
**Severity:** P1
**Effort:** 2-3 hours

---

### REQ B4 — Brand-context auto-injection (consistency across recipes)
**Severity:** P0 (the FAMtastic-brand-specific moat)
**Description:** Recipe skill prompt templates are generic. Without brand context, recipes can't produce on-brand output reliably. The wrapper:
1. Reads `~/famtastic/brand/FAMTASTIC-BRAND-MARK.md` (canonical manifesto).
2. Reads `~/famtastic/brand/BRAND-CONTEXT.md` (per-recipe-category context blocks — to be created).
3. Auto-prepends the relevant context block to every recipe invocation's prompt.
4. Recipe-category mapping:
   - Logo recipes → per-letter color rules, F=blue, A=tallest-yellow, M=red, "tastic" plain
   - Brand-kit / design-guide recipes → palette hex codes, typography pairings, visual rules
   - Video recipes → animation beats from `FAMTASTIC-BRAND-MARK.md`
   - Social/ad recipes → brand voice + tagline catalog
**Affected components:** wrapper prompt-template layer; new `brand/BRAND-CONTEXT.md` file
**Estimated effort:** 3-4 hours (file authoring + template-merge logic)
**Verification:** spot-check 5 recipes — every output references at least 2 brand-context elements (colors, typography, manifesto language).

---

### REQ B5 — Asset categorization & metadata
**Severity:** P1
**Description:** The 16 outputs from today's experiment are scattered across muapi-outputs/ with no organization. The wrapper:
1. Tags every output at generation time with: `recipe`, `category`, `model_used`, `prompt_hash`, `timestamp`, `cost_credits`, `success` (bool).
2. Stores metadata in `media-studio/data/assets.sqlite` (or JSONL — pick the lighter option).
3. Exposes a query CLI: `media-studio assets --category logo --since 2026-05-19 --min-quality 4`.
4. Each output goes to `media-studio/output/<recipe>/<timestamp>-<hash>.<ext>` instead of flat dump.
**Affected components:** wrapper output handling; new asset DB
**Estimated effort:** 3 hours
**Verification:** generate 5 outputs across categories, query each by category, return correct results.

---

### REQ B6 — Cost ledger
**Severity:** P1
**Description:** Need real-time visibility into muapi spend. The wrapper:
1. Captures per-call cost from muapi response metadata (if exposed) OR queries `muapi account balance` before+after.
2. Maintains a running total per session, per recipe, per category.
3. Pre-flight estimation: `media-studio plan run muapi-logo-branding` → "Estimated 100 credits ≈ $X"
4. Daily/weekly cost report.
**Affected components:** wrapper post-call handling
**Estimated effort:** 2-3 hours
**Verification:** match wrapper's tally against muapi account dashboard at end of week, ±1% accuracy.

---

### REQ B7 — Final-assembly curation
**Severity:** P1
**Description:** After running multiple recipes (e.g. logo-branding + brand-kit + design-guide + 3d-logo-animation), the wrapper assembles a curated deliverable package:
1. Picks the highest-quality output per category (using OCR pass + composition similarity + manual quality tags).
2. Generates a single PDF brand book combining: logo variations + palette card + typography sheet + UI kit + mockups + animation thumbnail.
3. Bundles transparent PNG layers for each component.
4. Outputs to `media-studio/deliverables/<brand>/<timestamp>/` with a `README.md` index.
**Affected components:** wrapper output pipeline; PDF assembly library (e.g. `pdf-lib`)
**Estimated effort:** 6-8 hours (PDF assembly is the long pole)
**Verification:** run the wrapper end-to-end for a fresh brand; assert deliverable folder contains: brand-book.pdf, /logo/, /palette/, /typography/, /mockups/, /video/, README.md.

---

## Section C — Strategic / cross-cutting

### STRAT C1 — Adobe subscription cancellation
**Severity:** P2 (cost optimization)
**Observed:** muapi covers 90%+ of Adobe Firefly's image-generation surface area at lower cost. Adobe Creative Cloud subscription (~$60/mo) only justified by manual GUI editing in Photoshop/Illustrator.
**Proposed action:** Cancel Adobe Creative Cloud subscription. Redirect the $60/mo budget into muapi credits.
**Affected components:** none technical; billing decision
**Estimated effort:** 5 minutes
**Verification:** Adobe subscription canceled in account; muapi credit balance increased.

---

### STRAT C2 — Build Media Studio in phases (not all-at-once)
**Severity:** P2 (process)
**Proposed sequencing:**
- **Phase 1 (now):** Implement REQ B1, B2, B4, A1, A4 — these unblock high-quality output. Sufficient to ship.
- **Phase 2:** Add REQ B5, B6 — operational visibility.
- **Phase 3:** Add REQ B7 — curated deliverables.
- **Phase 4:** UI on top of all of the above.
- Each phase ends with a Hermes-style review + solutions pass on whatever new gaps surface.
**Estimated effort:** ~30 hours of focused work to reach Phase 3-complete.

---

### STRAT C3 — Document the muapi-recipe-first standing rule project-wide
**Severity:** P1
**Proposed action:**
- Add a one-liner to `~/famtastic/CLAUDE.md`: *"For brand/media work, always check `muapi-<purpose>` recipe skills before hand-rolling primitives."*
- Memory entry already saved (2026-05-19).
- Cross-reference in `SITE-LEARNINGS.md` (already done).
**Estimated effort:** 5 minutes
**Verification:** rule appears in CLAUDE.md and is auto-loaded by future Claude sessions.

---

## Section D — What's NOT a gap (intentional clarification)

- **Manual primitive use is not deprecated.** Recipes are the default; primitives remain valid for genuinely novel work or single-prompt experiments. The wrapper's job is to make recipes the FRICTIONLESS default, not to forbid primitives.
- **Brand mark manifesto is not muapi's responsibility.** The strategic thinking (per-letter colors, story, architecture) is HUMAN work + Claude pairing. muapi executes against the manifesto; it doesn't create it.
- **Remotion is not redundant.** It owns the brand-locked composition layer (GAP A4's Stage 2), live-player embedding in sites, and programmatic per-site customization. muapi can't do these.

---

## Summary roll-up

| Section | Items | Total effort |
|---|---|---|
| A — muapi limitations | 6 gaps | ~12 hours |
| B — wrapper requirements | 7 reqs | ~22 hours |
| C — strategic | 3 items | ~30 hours sequential build |
| **TOTAL TO MEDIA STUDIO V1** | **16 items** | **~30 focused hours over ~6 sessions** |

This backlog drives the next 6 Media Studio build sessions. Each item has
a concrete solution, sized effort, and verification criteria — no
ambiguous work remaining at the planning level.

**Next session-start move:** pick item from Section B Phase 1 (REQ B1 or
REQ B4 are the highest-leverage), implement, verify, mark done, repeat.
