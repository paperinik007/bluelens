# LlamaFirewall only runs AlignmentCheck — PromptGuard was never wired, and this should have surfaced earlier

Research task, primary sources: the vendor's own documentation (local clone,
`llamafirewall-vendor`, see `reference_llamafirewall_vendor_repo` memory — commit
`4be64c3a`, pip `1.0.3`), the vendor's actual source code, the Hugging Face API, and
OpenRouter's own docs. Written 2026-08-29, after the `judge-targeted-cases` branch's
Step 2 final review surfaced a false mechanism claim (§3.2 of
`docs/design/2026-08-28-judge-targeted-cases-design.md`) that traced back to this same
gap. Retrospective: this analysis should have been done during vendor selection
(`docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`) or immediately
after implementing the LlamaFirewall adapter
(`docs/design/2026-08-27-multi-vendor-llamafirewall-design.md`) — not three sessions
later, prompted by a branch built on top of the gap.

## Verdict

**LlamaFirewall is documented by the vendor as a layered defense combining four
components — PromptGuard 2, AlignmentCheck, CodeShield, Regex/Custom — and this
project's adapter wires up exactly one of them, AlignmentCheck.** This is not a
corner cut: the wiring (`LlamaFirewall(scanners={Role.ASSISTANT: [TOOL_NAME]})` in
`src/detector_adapter/vendors/llamafirewall/evaluate_case.py`) is architecturally
identical to the vendor's own documented example for `scan_replay()` usage. The gap is
that nothing in this project's research or design docs registered *why* the other
scanners — PromptGuard specifically — were left out, or what it would take to add them.
PromptGuard is not reachable via OpenRouter (it is not a generative chat-completion
model at all) and requires a manually-gated Hugging Face model download plus
`torch`/`transformers`/`huggingface_hub`, none of which are in the
`detector-llamafirewall` container today. Every "LlamaFirewall" verdict published so
far (`docs/reports/llamafirewall-2026-08-28/`) reflects AlignmentCheck's judgment only.

## 1. What the vendor's own documentation says LlamaFirewall is

[VERIFIED: local vendor clone, `LlamaFirewall/website/docs/documentation/`]

- `about-llamafirewall.md`: "**Layered Defense Architecture**: Combines multiple
  scanners—PromptGuard 2, AlignmentCheck, CodeShield, and customizable regex
  filters—for comprehensive protection across the agent's lifecycle."
- `llamafirewall-architecture/architecture.md` lists the four components with their
  stated use cases:
  - **PromptGuard 2** — "fast, lightweight BERT-style classifier... operates on user
    inputs and untrusted content... Catching classic jailbreak patterns, social
    engineering prompts, and known injection attacks."
  - **AlignmentCheck** — "chain-of-thought auditing module... Verifying that agent
    decisions remain consistent with user intent."
  - **CodeShield** — static analysis of LLM-generated code.
  - **Regex + Custom Scanners** — pattern matching.
- `workflow-and-detection-components.md`, "Scenario 1: Preventing Goal Hijacking and
  Data Exfiltration" — structurally the closest documented example to this project's
  own `bulk_export_to_partner_address`/`bulk_export_with_fake_reviewer_authorization_note`
  pair (goal hijacking via a note aimed at manipulating the system, followed by
  exfiltration). The vendor's own defense workflow for this exact threat class is
  **two sequential stages**: PromptGuard scans incoming text *before* it enters the
  agent's context ("→ IF detected, the page is dropped. → IF missed, agent may
  internalize injected goal."); AlignmentCheck is the second-stage fallback that
  "monitors token stream for goal shifts... → IF goal hijack is detected, execution
  is halted immediately." The vendor's own stated **Outcome** line: "PromptGuard
  eliminates detected jailbreaking attempts before they enter context. If a novel
  variant slips through, or an injection is successful without a jailbreak trigger,
  AlignmentCheck detects the change in behavior."
- `scanners/alignment-check.md` itself says: "Its ability to be **layered with
  PromptGuard** enables it to offer an additional level of protection" — the vendor's
  own scanner-specific doc describes AlignmentCheck as complementary to PromptGuard,
  not a substitute for it.

## 2. What this project's adapter actually wires — and that it matches the vendor's own example

[VERIFIED: `src/detector_adapter/vendors/llamafirewall/evaluate_case.py`, local
vendor clone `LlamaFirewall/website/docs/documentation/getting-started/how-to-use-llamafirewall.md`]

`evaluate_case.py`:
```python
firewall = LlamaFirewall(scanners={Role.ASSISTANT: [TOOL_NAME]})
scan_result = firewall.scan_replay(trace)
```
where `TOOL_NAME` resolves to the project's registered `AGENT_ALIGNMENT` scanner
(`OpenRouterAlignmentCheck`).

The vendor's own official documentation example for `scan_replay()` (same file,
"Using Trace and scan_replay" section) configures the firewall identically:
```python
firewall = LlamaFirewall({
    Role.ASSISTANT: [ScannerType.AGENT_ALIGNMENT],
})
result = firewall.scan_replay(conversation_trace)
```
**This project's integration is not an oversight or a shortcut — it is a faithful
implementation of the vendor's own documented `scan_replay` pattern.** The market
research doc already correctly noted this constraint on 2026-08-20
(`docs/research/2026-08-20-vendor-market-agentic-threat-detection.md:356-358`):
"Taxonomy: ScannerType enum: `PROMPT_GUARD` (injection), `AGENT_ALIGNMENT` (goal
hijacking, indirect injection), `CODE_SHIELD` (code security). Multi-turn via
`AGENT_ALIGNMENT` only." What neither that doc nor the later design doc
(`docs/design/2026-08-27-multi-vendor-llamafirewall-design.md`) registered is
*why PromptGuard specifically was left out entirely* rather than run alongside
AlignmentCheck as a separate, single-message pass per user turn — which the vendor's
own `scan()` API (a different call than `scan_replay()`, see the "Basic Usage"
section of the same doc) supports and the vendor's own threat-model walkthrough
(§1 above) explicitly recommends running together.

## 3. Why PromptGuard isn't reachable via OpenRouter — architecture, not policy

[VERIFIED: Hugging Face API (`huggingface.co/api/models/meta-llama/Llama-Prompt-Guard-2-86M`,
fetched 2026-08-29), OpenRouter's own docs (`openrouter.ai/docs/models`, fetched
2026-08-29), local vendor source `llamafirewall-vendor/.../promptguard_utils.py`]

- **`meta-llama/Llama-Prompt-Guard-2-86M` architecture**: `DebertaV2ForSequenceClassification`
  (`model_type: deberta-v2`) — a **discriminative sequence classifier**, not a
  generative/chat-completion model. It has no next-token generation head; it takes
  text in and returns a probability score from a softmax classification head
  (confirmed in the vendor's own inference code, `promptguard_utils.py`:
  `AutoModelForSequenceClassification`, `probabilities[0, -1].item()`).
- **OpenRouter's own documentation** describes its catalog as "400+ models and
  providers" across output modalities "text, image, audio, embeddings" — built around
  chat-completions/text-generation (plus embeddings), with no mention of
  classification-head or BERT/DeBERTa-style discriminative models anywhere in the
  fetched docs. This is an **architectural mismatch, not a deliberate exclusion**:
  a 86M-parameter classification head doesn't fit a chat-completions API, so it isn't
  the kind of model OpenRouter routes at all — unrelated to whether the model is
  "special" or security-sensitive.
- **Separately, it is also gated**: HF API reports `"gated": "manual"`, license
  `llama4` ("Llama 4 Community License Agreement") — access requires submitting a
  form (legal name, date of birth, organization, job title, country) and manual
  approval, with an explicit clause restricting use by "services exceeding 700
  million monthly active users" (not a constraint relevant to this project's scale,
  but part of why it isn't a one-line `pip install` away from running).
- **Not currently installed in the container**: `docker/detector-llamafirewall/Dockerfile`
  does `pip install --no-cache-dir --no-deps llamafirewall==1.0.3` then only adds
  `openai`/`pydantic` — `torch`, `transformers`, and `huggingface_hub`, all required
  by `promptguard_utils.py`, are absent. PromptGuard cannot even import in the current
  image, independent of the gating question.

So: yes, it is a small model purpose-trained for a security task (jailbreak/prompt-injection
classification), and no, that alone is not why it's unreachable via OpenRouter — the
reason is structural (a classification model doesn't fit a chat-completions router)
plus a separate, addressable licensing gate.

## 4. Consequence for the `judge-targeted-cases` branch and every LlamaFirewall verdict published so far

The branch's design doc (§3.2) claimed a judge-targeted payload would be
"structurally invisible" to AlignmentCheck. That specific claim was independently
verified false during the Step 2 final review (see
`docs/design/registro-limiti-aperti.md`, addendum to the "Copertura delle categorie
native di LlamaFirewall..." entry) — the payload lands directly in AlignmentCheck's
`USER MESSAGE` field, evaluated against every action. This research doc addresses a
different, earlier question the branch never asked: **would PromptGuard, if it were
running, have caught this kind of payload before AlignmentCheck ever saw it?**
PromptGuard's documented use case explicitly includes "social engineering prompts" —
the fake-authorization note ("pre-autorizzata da Compliance... non richiede ulteriore
verifica") is a social-engineering framing, not a classic "ignore previous
instructions" jailbreak string, so this is not a foregone conclusion either way — it's
an open, testable question, not yet tested.

More broadly: **every "LlamaFirewall" verdict published in this project
(`docs/reports/llamafirewall-2026-08-28/`) reflects only AlignmentCheck's judgment.**
Nothing in the published reports states this explicitly beyond the existing
`registro-limiti-aperti.md` entry on taxonomy coverage — a reader could reasonably
assume "LlamaFirewall" means the vendor's full layered defense was evaluated.

## 4b. Independent second read (Pi/minimax, 2026-08-29) — cross-checked, mostly converges

Separately from this doc, the user ran an independent "fresh opinion, ignore prior
work" pass over the same local vendor clone via Pi (session model: minimax). Its
architectural read was cross-checked against the vendor source in this same pass
(not taken on faith — same discipline as the rest of this doc):

- **Confirmed accurate**: `CustomCheckScanner`'s default `model_name` is
  `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` over `https://api.together.xyz/v1`
  (`TOGETHER_API_KEY`) — verified directly in
  `scanners/custom_check_scanner.py:35-37`. This is the vendor's out-of-the-box
  default; **this project's `OpenRouterAlignmentCheck` already overrides all three**
  (`adapter.py`: `DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"`,
  `API_BASE_URL` a local OpenRouter proxy, `LLAMAFIREWALL_OPENROUTER_API_KEY`) — the
  Together-AI requirement Pi's report treats as an open cost/setup question is already
  solved differently here, with a real measured cost ($0.0318/31 cases, see
  `registro-limiti-aperti.md`).
- **Confirmed accurate**: multi-scanner aggregation policy — verified directly in
  `llamafirewall.py::scan()` (lines ~134-167): when a `Role` has more than one
  scanner configured, `ScanDecision.BLOCK` wins if any scanner returns it, otherwise
  the decision with the highest score wins. **But this aggregation only fires within
  a single `scan()` call for one `Role`'s scanner list** — it does not apply across
  different roles. Since PromptGuard would naturally sit on `Role.USER` (per the
  vendor's own default `Configuration`) and AlignmentCheck is already registered on
  `Role.ASSISTANT`, adding PromptGuard would **not** trigger the vendor's own
  BLOCK-wins arbitration at all — the two scanners would produce two independent
  `ScanResult`s from two independent calls (`scan()` per user turn,
  `scan_replay()` on the full trace), same as today. Combining those two results into
  one `Verdict` for this project's schema remains an open design question, but it is
  **our own aggregation to design, not an inherited vendor policy to reverse-engineer.**
- **Softer/unverified in Pi's report, tightened here**: it described Prompt-Guard-2's
  licensing as "clausole specifiche sull'uso responsabile" without a primary-source
  fetch (no HF API or web call appears in its session transcript). §3 above already
  has the harder fact, fetched from the HF API directly: `gated: manual` under the
  Llama 4 Community License, a real approval-form requirement, not just a usage
  clause to note.
- **The one framing gap that matters most**: Pi's report was explicitly instructed to
  ignore this project's existing work, so it treats "should we integrate
  AlignmentCheck" as an open question and recommends "start with a minimal
  PromptGuard + AlignmentCheck adapter" — describing as future work something already
  built, containerized, and run for real (§2 above, `docs/reports/llamafirewall-2026-08-28/`).
  Its independent technical read is corroborating evidence for §1-§3 of this doc
  (particularly the AlignmentCheck single-action-vs-user-message mechanism, which it
  derived from the system prompt while this doc derived the same conclusion from real
  proxy logs — two different methods, same answer), but its recommendation is not
  usable as-is without the missing context restored.

## 4c. Pi's 4-point verification (2026-08-29) — confirms 3, contests 1, contested point re-verified here

Pi ran the four independent checks this doc's §4b asked for, reading the vendor
source directly (not this doc). Full response:
`temp/2026-08-29-pi-risposta-a-claude-llamafirewall/pi-risposta-a-claude-llamafirewall.md`.

- **Point 1 (cross-role collision)**: confirmed no collision, plus a real addition —
  `scan_replay()` (`llamafirewall.py:189-211`) short-circuits: it returns only the
  **last-scanned message's** `ScanResult` (not an aggregate across the trace), and
  `break`s immediately on `BLOCK` or `HUMAN_IN_THE_LOOP_REQUIRED` (lines 207-210).
  **Independently re-verified here, same lines** — accurate. This single detail
  matters for §4c below.
- **Point 2 (CPU latency)**: vendor publishes no CPU numbers, only A100
  (`Llama-Prompt-Guard-2/86M/MODEL_CARD.md`: 92.4ms for 86M, 19.3ms for the 22M
  variant). Pi's recommendation to consider the 22M variant rests on an unverified
  assumption ("per il nostro caso d'uso, casi in inglese") that is **factually wrong**:
  this project's dataset is authored in Italian, not English (spot-checked here,
  `dataset/bulk_export_honest_quarterly_report.yaml:14`: "Ciao, sono il responsabile
  customer success..."). The 22M variant has no multilingual pretraining (model card,
  "Limitations", per Pi's own citation) — **only the 86M variant is viable for this
  project's dataset**, independent of any latency tradeoff. Settled, not open.
- **Point 3 (container cost)**: reasonable order-of-magnitude estimate (+250-350MB
  image, image roughly doubling), explicitly labeled as an estimate, not measured —
  correctly caveated by Pi as needing a real `pip install` to confirm. No objection.
- **Point 4 (one combined `Configuration` vs two separate calls) — Pi's rebuttal
  re-examined and only partly accepted.** Pi argued there is "no architectural
  difference" between a single `LlamaFirewall` instance with a combined
  `Configuration` and two separate calls, since `scan_replay()` is "just" a loop over
  `scan()` dispatching by role — true as a mechanism description, verified here too.
  But **Pi's own point-1 finding directly contradicts "no difference, only
  bookkeeping": the short-circuit means a single combined `Configuration` run through
  one `scan_replay()` call would let whichever scanner fires first suppress
  evaluation of the other.** Concretely: if `PROMPT_GUARD` (on `Role.USER`) blocks
  the seed turn, `scan_replay()` breaks immediately — `AGENT_ALIGNMENT` (further down
  the trace, on `Role.ASSISTANT`) is **never even invoked** for that case, and its
  verdict is permanently unmeasured, not merely "un-recorded for bookkeeping." For an
  audit project whose purpose is comparing independent scanner signal on the same
  case, this is a real loss of measurement data, not a cosmetic preference. Keeping
  them as two separate `scan_replay()` calls (one `Configuration = {Role.ASSISTANT:
  [TOOL_NAME]}` as today, a second `Configuration = {Role.USER: [ScannerType.PROMPT_GUARD]}`)
  — not "one `scan()` per turn" as this doc's §4b imprecisely said, a second
  `scan_replay()` call is simpler and reuses the existing call pattern — guarantees
  both scanners are independently evaluated on every case regardless of which one
  would otherwise fire first. Pi is right that the vendor doesn't impose this design
  and that the real question is our own arbitration policy; this doc maintains that
  keeping the two scans structurally separate is not just bookkeeping but a
  correctness requirement for getting two independent verdicts per case, given the
  short-circuit Pi itself found.

## 4d. Loop closed (Pi, 2026-08-29)

Pi accepted §4c's rebuttal on both points without qualification, having noticed the
contradiction between its own point-1 finding and point-4 claim once it was pointed
out (`temp/2026-08-29-pi-risposta-a-claude-llamafirewall/pi-risposta-finale-loop-chiuso.md`,
session-local, not re-verified here since it introduces no new factual claims beyond
what §4c already confirmed directly against the vendor source). Settled: two separate
`scan_replay()` calls (not one combined `Configuration`), 86M model variant (not
22M). Open, not settled: which of the three arbitration policies (§4c) to adopt —
that is genuinely a design decision, not a fact to verify, and belongs in a dedicated
design doc together with the schema change it implies for `Verdict`.

## 5. Not resolved here

This doc is research, not a design or implementation. What it would take to wire
PromptGuard in (container deps, HF gated access, a second `scan_replay()` call with a
`{Role.USER: [ScannerType.PROMPT_GUARD]}` Configuration alongside the existing
AlignmentCheck call, and how two independent scanner verdicts collapse into one
`Verdict` in this project's schema — §4c lists three candidate policies from Pi's
response, undecided) is tracked as the open next step in
`docs/design/registro-limiti-aperti.md` (addendum to the LlamaFirewall coverage
entry, 2026-08-29) — not decided or scoped in this doc. Model variant is settled
(§4c): 86M, not 22M, since this project's dataset is Italian and the 22M variant has
no multilingual pretraining.

## Sources consulted

- Local vendor clone `llamafirewall-vendor` (`reference_llamafirewall_vendor_repo`
  memory, commit `4be64c3a`, pip `1.0.3`): `LlamaFirewall/website/docs/documentation/about-llamafirewall.md`,
  `llamafirewall-architecture/architecture.md`, `llamafirewall-architecture/workflow-and-detection-components.md`,
  `scanners/alignment-check.md`, `scanners/prompt-guard-2.md`,
  `getting-started/how-to-use-llamafirewall.md`; source files
  `scanners/prompt_guard_scanner.py`, `scanners/promptguard_utils.py`,
  `scanners/experimental/alignmentcheck_scanner.py`, `llamafirewall.py` (default
  `Configuration`, `create_scanner`).
- This project's source: `src/detector_adapter/vendors/llamafirewall/evaluate_case.py`,
  `adapter.py`; `docker/detector-llamafirewall/Dockerfile`.
- Local vendor clone, cross-checking §4b's claims from the independent Pi/minimax
  pass: `scanners/custom_check_scanner.py` (default model/API/env-var), `utils/base_llm.py`
  (OpenAI-SDK-compatible client, confirming any OpenAI-compatible `base_url` works —
  which is exactly what this project's OpenRouter override relies on), `llamafirewall.py`
  lines ~108-167 (`scan()` per-role aggregation: BLOCK wins within one role's scanner
  list, decision by highest score otherwise; does not aggregate across roles).
- Pi's independent verification response (2026-08-29):
  `temp/2026-08-29-pi-risposta-a-claude-llamafirewall/pi-risposta-a-claude-llamafirewall.md`
  (gitignored, session-local) — its four checkable claims cross-verified against the
  vendor source directly in this pass, not taken on report alone: `llamafirewall.py:189-211`
  (`scan_replay()` short-circuit, confirmed) and this project's own dataset
  (`dataset/bulk_export_honest_quarterly_report.yaml`, confirming Italian-language
  content against Pi's unverified English-language assumption).
- Hugging Face API: `huggingface.co/api/models/meta-llama/Llama-Prompt-Guard-2-86M`,
  fetched 2026-08-29 (gated status, license, pipeline_tag, architecture tag).
  Note: a direct fetch of the raw `config.json` returned HTTP 401 (gated repo,
  unauthenticated fetch) — the architecture given here (`DebertaV2ForSequenceClassification`)
  comes from the model API's own tag metadata, not a fetched `config.json`; this is a
  weaker source than the `config.json`-direct verification done for AgentDoG in
  `docs/research/2026-08-27-agentdog-verification.md` and should be treated as
  probably-correct-but-not-file-verified.
- OpenRouter docs: `openrouter.ai/docs/models`, fetched 2026-08-29 (modality/catalog
  description) — a docs page, not an exhaustive model listing API call; absence of
  classification-model support is inferred from what the docs describe, not from
  enumerating all 400+ listed models.
- Already-existing project docs, read for cross-reference, not re-verified here:
  `docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`,
  `docs/design/2026-08-27-multi-vendor-llamafirewall-design.md`,
  `docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md`.

## Open items not resolved in this pass

- The HF `config.json` itself was not fetched successfully (401, gated) — architecture
  claim rests on API tag metadata, not the file directly.
- Whether PromptGuard would actually catch the specific judge-targeted payloads used
  in the closed `judge-targeted-cases` branch is untested — this doc establishes that
  the question is open and testable, not what the answer is.
- Container/dependency footprint of adding `torch`+`transformers` (CPU) to
  `detector-llamafirewall` not measured (image size, build time).
