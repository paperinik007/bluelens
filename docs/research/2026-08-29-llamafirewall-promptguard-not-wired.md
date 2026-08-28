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

## 5. Not resolved here

This doc is research, not a design or implementation. What it would take to wire
PromptGuard in (container deps, HF gated access, a second `scan()` pass per user turn
alongside the existing `scan_replay()` pass, and how two scanner verdicts collapse
into one `Verdict` in this project's schema) is tracked as the open next step in
`docs/design/registro-limiti-aperti.md` (addendum to the LlamaFirewall coverage
entry, 2026-08-29) — not decided or scoped in this doc.

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
