# Prior art: open-source harnesses/datasets for LLM-agent security, and whether any of it fits this project's need

Research task, primary sources only (GitHub API/READMEs, arXiv abstracts/PDFs, official docs — no
secondary blog posts trusted as source of truth). Triggered by a direct challenge: did anyone check
whether the toy-agent/container architecture and the hand-authored Plan 5 dataset could instead have
reused existing work? Answers that honestly, against the specific need stated in `SPIRIT.md`: acting
as an **independent third-party auditor** that verifies whether a **separate detector/defense tool**
(here: `aidr`'s Sifter/Inspector/Gauntlet) catches what it claims — not red-teaming an agent's own
safety behavior.

## Summary

No project found does what this repo's architecture does: run a real agent against a real tool
surface, hand the resulting transcript to a structurally separate, network-isolated, arbitrary
black-box detector, and score that detector's own claims. Every established benchmark investigated
(AgentDojo, InjecAgent, ASB, AgentHarm, ToolEmu, AgentBench) treats "defense" as a pluggable
component *inside* its own harness, evaluated in the same process as the attack and the agent — that
is agent/defense red-teaming, a different problem from third-party detector auditing. Three newer,
less-established projects (R-Judge, TraceSafe, AgentAuditor/ASSEBench) get structurally closer —
they score a judge/guardrail against a labeled transcript — but none exposes a "point this at your
own external detector container and get P/R/F1" interface, and the closest one (TraceSafe) is two
weeks old, gated, and unvalidated by the field. No dataset found uses MITRE ATLAS/ATT&CK-style
technique codes, and none uses `aidr`'s own 14-technique taxonomy — every project has its own,
mutually inconsistent one, a finding independently confirmed by a 2026 meta-survey covering 40 such
benchmarks. Verdict: the custom architecture was justified and should not be replaced retroactively;
hand-authoring the Plan 5 dataset is still the right call for this round, with these external
projects used only as coverage cross-checks (as the existing prep note already concluded, now backed
by deeper primary-source verification) and, later, as inspiration for a mutation-based scaling
approach once the toy agent's own tool surface is established.

---

## Question 1 — established harnesses/benchmarks, verified

Method: GitHub REST API (`gh api repos/<owner>/<repo>`) for license/dates/activity — this is the
platform's own metadata, treated as primary. arXiv abstracts fetched directly. Dates below are as of
2026-08-19 (`pushed_at` = last commit to the default branch).

| Project | Repo | License | Last push | Stars | Detector-under-test? |
|---|---|---|---|---|---|
| AgentDojo | `ethz-spylab/agentdojo` | MIT | 2026-06-02 | 757 | No — defenses run in-process |
| InjecAgent | `uiuc-kang-lab/InjecAgent` | MIT | 2024-07-02 (stale) | 159 | No — attack-only, single-step |
| AgentHarm | via `UKGovernmentBEIS/inspect_evals` | MIT + field-of-use clause | 2026-08-19 (active) | 632 (host repo) | No — self-graded jailbreak compliance |
| R-Judge | `Lordog/R-Judge` | none found (no LICENSE file) | 2026-01-11 | 110 | Partial — judges a transcript, but as raw LLM capability, not a pluggable audited product |
| Agent Security Bench (ASB) | `agiresearch/ASB` | MIT | 2026-04-16 | 287 | No — 11 defenses baked into the same harness |
| Meta CyberSecEval 3/4 | `meta-llama/PurpleLlama` | Llama 3.2 Community License (non-OSI); GitHub reports `NOASSERTION` | 2026-08-18 (active) | 4358 | No — CyberSOCEval evaluates malware/threat-intel analysis P/R, not agent tool-call detection |
| ToolEmu | `ryoungj/ToolEmu` | Apache-2.0 | 2024-03-22 (stale) | 218 | Partial — has a distinct "LM safety evaluator," but it's the benchmark's own built-in judge |
| AgentBench | `THUDM/AgentBench` | Apache-2.0 | 2026-02-08 | 3675 | N/A — general capability eval, no security component at all |

Found during research, not in the original list — closer to the actual need and worth registering:

| Project | Repo | License | Last push | Stars | Detector-under-test? |
|---|---|---|---|---|---|
| GuardBench | `AmenRa/GuardBench` | EUPL-1.2 | 2025-10-09 | 39 | Yes, but chat/content-moderation models only — no agent tool-call trajectories |
| AgentAuditor / ASSEBench | `Astarojth/AgentAuditor-ASSEBench` | Apache-2.0 | 2026-05-29 | 42 | AgentAuditor *is* a proposed detector/evaluator (not an audit harness for third parties); ASSEBench aggregates AgentHarm/R-Judge-style data as ground truth |
| TraceSafe / TraceSafe-Bench | `cycraft-corp/TraceSafe` (paper: arXiv 2604.07223) | Apache-2.0 | 2026-08-07 (12 days old) | 1 | **Closest match found** — scores 13 LLM-as-guard models + 7 specialized guardrails against ground-truth multi-step tool-call trajectories |
| AgentDoG | `AI45Lab/AgentDoG` | Apache-2.0 | 2026-08-19 (active) | 682 | Itself a vendor detector product (like `aidr`) graded on its own benchmark family (ATBench) — same conflict-of-interest structure this project already refuses to trust for `aidr`'s Gauntlet |

### Per-project detail

**AgentDojo** [VERIFIED: `ethz-spylab/agentdojo` README + gh api]. "A Dynamic Environment to Evaluate
Attacks and Defenses for LLM Agents" — NeurIPS 2024, Debenedetti et al. 97 realistic tasks + 629
security test cases across 4 domains (Workspace, Slack, Travel, Banking), joint utility+security
scoring, latest tagged release v0.1.35 (2025-10-27), still actively pushed. Defenses — including a
`transformers`-based "prompt injection detector" — are installed as an extra and run as part of the
*same* agent pipeline the harness drives; there is no notion of handing a transcript to an external,
independently-running black-box product and scoring its verdict. This is attack-vs-defense
red-teaming of one integrated system, not third-party audit.

**InjecAgent** [VERIFIED: arXiv:2403.02691 abstract, gh api]. 1,054 test cases, 17 user tools + 62
attacker tools, evaluates indirect-prompt-injection vulnerability; ReAct-prompted GPT-4 found
vulnerable 24% of the time. MIT license. Last push 2024-07-02 — effectively unmaintained (open issues
sit at 4, no recent activity). Purely "attack an agent, see if it complies" — average trajectory
length is reported elsewhere as 1 (single-step), no detector concept at all.

**AgentHarm** [VERIFIED: arXiv:2410.09024 abstract, `ukgovernmentbeis.github.io/inspect_evals`
page]. 110 explicitly malicious agent tasks (440 with augmentations), 11 harm categories, released
by the UK AI Safety Institute, now maintained inside `UKGovernmentBEIS/inspect_evals` rather than as
a standalone repo (no standalone repo found under the AI-Safety-Institute org as of this check).
License is "MIT with an additional clause" restricting use to purposes that improve AI safety/security
— a real field-of-use restriction to flag if ever reused. Grading uses the benchmark's own
"refusal judge" + "semantic judge" (both GPT-4o by default) — this *is* an evaluator, but it's the
benchmark's built-in judge assessing the agent's compliance, not an external product's claims being
verified against ground truth.

**R-Judge** [VERIFIED: arXiv:2401.10019 abstract, `Lordog/R-Judge` repo]. 569 records of multi-turn
agent interaction, 27 risk scenarios, 5 application categories, 10 risk types, EMNLP Findings 2024.
Best model (GPT-4o) scores 74.42%. **No LICENSE file exists in the repo** — `gh api
repos/Lordog/R-Judge/license` returns 404, and `license` is `null` in the repo metadata; reuse/
redistribution rights are legally unclear. This is structurally the closest of the "classic" set to
the actual need: it hands a pre-recorded transcript to a judge and checks whether the judge correctly
flags risk. But it benchmarks the judging LLM's raw capability across many models, not a specific
vendor's shipped detector product, and offers no "plug in your own external detector" interface.

**Agent Security Bench (ASB)** [VERIFIED: arXiv:2410.02644 abstract, `agiresearch/ASB` repo]. ICLR
2025, Zhang et al. 10 scenarios, 10 agents, 400+ tools, 27 attack/defense types, 7 metrics, 13 LLM
backbones; best attack success rate 84.30%, defenses show limited effectiveness. MIT license, pushed
2026-04-16. Same pattern as AgentDojo: 11 defenses are evaluated as components integral to the same
framework, not as independently-running products under audit.

**Meta CyberSecEval 3/4 (PurpleLlama)** [VERIFIED: `meta-llama/PurpleLlama/CybersecurityBenchmarks`
README, gh api]. Agentic suites: "Autonomous Offensive Cyber Operations" (tests an LLM acting as an
attack agent in a simulated network), AutoPatchBench (LLM agent patches vulnerabilities in native
code), and CyberSOCEval (built with CrowdStrike — malware-analysis and threat-intel-reasoning P/R).
CyberSOCEval's malware-analysis leg is the nearest thing to "precision/recall of a detector" in this
whole family, but it evaluates static malware/report analysis, not multi-step agent tool-call
trajectories — a different data modality from what this project measures. Root repo `LICENSE` is the
Llama 3.2 Community License (naming/attribution obligations, not an OSI-approved license); GitHub's
license detector reports `NOASSERTION` accordingly. Very actively maintained (pushed 2026-08-18).

**ToolEmu** [VERIFIED: arXiv:2309.15817 abstract, `ryoungj/ToolEmu` repo]. ICLR'24 Spotlight. An LM
emulates tool execution (no real tool implementations needed) across 36 high-stakes tools and 144
test cases; a separate "LM-based automatic safety evaluator" grades agent failures, validated at
68.8% agreement with real-world failures. Apache-2.0. Last push 2024-03-22 — over two years stale.
Architecturally the most "detector-shaped" of the pre-2025 benchmarks (explicit separation between
the tool-emulating environment and the safety evaluator), but the evaluator is the benchmark's own
built-in judge, and the tools themselves are LM-emulated rather than real code — the opposite of this
project's insistence (per the existing SourceLens design decisions) that tool behavior be real,
static code, never fabricated for the detector's benefit.

**AgentBench** [VERIFIED: arXiv:2308.03688 abstract, gh api]. ICLR 2024, 8 environments, general
agent capability evaluation (reasoning, instruction-following) — explicitly has no security, safety,
or red-teaming component. Included only to confirm it is out of scope, as instructed.

**GuardBench** [VERIFIED: `AmenRa/GuardBench` README, gh api]. A Python library unifying 40
evaluation datasets behind one interface specifically to benchmark guardrail *models* (LLMs
fine-tuned to flag unsafe content) with precision/recall/F1/MCC/FPR/etc. EUPL-1.2, pushed
2025-10-09. This is the right *shape* of tool for detector auditing — but its input unit is a chat
conversation, not an agent tool-call trajectory; it has no concept of tool calls, ReAct steps, or
multi-turn agent execution at all. Not usable for this project's domain as-is.

**AgentAuditor / ASSEBench** [VERIFIED: `Astarojth/AgentAuditor-ASSEBench` README, gh api].
AgentAuditor is "a universal, training-free, memory-augmented reasoning framework" that makes an LLM
evaluator emulate expert human judgment on agent safety/security risk (semantic annotation →
clustering → CoT demonstration generation → RAG → few-shot inference). ASSEBench is its accompanying
benchmark, built by aggregating AgentHarm/AgentJudge/R-Judge-style data, organized by risk category
and outcome type. Apache-2.0, pushed 2026-05-29. Important distinction: AgentAuditor is *itself a
proposed detector*, competing with the very category of product `aidr` is — not a neutral third-party
harness for auditing an arbitrary external detector. Its underlying ASSEBench data could in principle
serve as ground truth for someone else's detector, but that use case is not what the project builds
or documents.

**TraceSafe / TraceSafe-Bench** [VERIFIED: arXiv:2604.07223 (v2, 2026-08-11) abstract/PDF,
`cycraft-corp/TraceSafe` + `yenshan0530/TraceSafe` repos, `huggingface.co/datasets/CyCraftAI/
TraceSafe`]. From CyCraft AI (a Taiwan-based cybersecurity vendor), Chen/Huang/Yang/Chen. This is the
single closest match found to the project's actual need: it evaluates 13 LLM-as-a-guard models plus
7 specialized guardrail products against ground-truth-labeled, multi-step tool-calling trajectories,
across 12 risk categories (prompt injection, privacy leakage, hallucination, interface
inconsistencies, etc.) plus a benign baseline, explicitly to measure whether guardrails hold up
mid-trajectory rather than only at the final output. Repo pushed 2026-08-07 — 12 days before this
research was written; 1 GitHub star; dataset access on HuggingFace is gated (request-based). No
evidence yet of independent adoption, replication, or scrutiny by the field. Genuinely the strongest
external precedent for "detector auditing" as a first-class framing, but far too new and unvalidated
to be treated as a dependable primary source for anything beyond a pointer to revisit later.

**AgentDoG** [VERIFIED: `AI45Lab/AgentDoG` README, gh api]. From Shanghai AI Lab (AI45Lab). A
"lightweight and scalable agent safety alignment framework" that is simultaneously (a) a detector
model deployable as a runtime guardrail and (b) a benchmark family (ATBench / ATBench-Claw /
ATBench-Codex) it grades itself against with accuracy/P/R/F1, claiming competitive results against
larger frontier models. Apache-2.0, pushed today (2026-08-19) — actively maintained, 682 stars, the
most adopted of the newly found projects. Structurally this occupies the *vendor* position in this
project's own model, not the *auditor* position: it is a detector graded on a benchmark it (or its
close collaborators) built, the exact conflict-of-interest pattern `SPIRIT.md` principle 1 already
refuses to accept for `aidr`'s own Gauntlet. Not usable as neutral ground truth without the same
independent verification this project already insists on for `aidr`.

### Field-level corroboration

**"Safety, or Just Capability? A Validity Audit of Agent-Safety Benchmarks"** [VERIFIED:
arXiv:2607.28685 abstract]. An empirical audit of existing agent-safety benchmarks finding: (a) a
naive "always positive" policy already scores above F1 = 2π/(1+π) on binary benchmarks — the metric
rewards uninformative classifiers; (b) three tested benchmarks rank the same 18 models
*differently* — they do not measure a shared construct; (c) capability correlates *negatively*
(ρ = -0.44) with measured misalignment safety in at least one comparison, suggesting benchmark scores
partly reflect capability rather than genuine safety. Core recommendation: any safety claim needs to
name its benchmark, metric, target behavior, and model panel explicitly to be meaningful — precisely
the discipline `SPIRIT.md` principle 2 already imposes on this project.

**"Taxonomy and Consistency Analysis of Safety Benchmarks for AI Agents"** [VERIFIED:
arXiv:2605.16282 abstract]. First systematic cross-benchmark analysis, cataloging 40 behavioral
agent-safety benchmarks. Finds "no evidence of ranking concordance across evaluation dimensions"
(Kendall's W = 0.10, p = 0.94), inconsistent threat models, incompatible metrics, and overlapping-yet
-incomplete risk coverage across the field; coverage counts are found to systematically overstate
real evaluation depth. Independently confirms, at field scale, what the per-project review above
found one project at a time: there is no consensus taxonomy this project could adopt wholesale, and
"benchmark X covers technique Y" claims in this space need direct verification rather than trust.

---

## Question 2 — reusable datasets with ground-truth labels

None of the datasets surveyed use MITRE ATLAS/ATT&CK-style technique codes — confirmed by targeted
search (`AgentDojo OR InjecAgent OR "Agent Security Bench" "MITRE ATLAS" OR "ATT&CK"`) returning no
project connecting itself to that taxonomy. Every project defines its own labels.

| Dataset | Size | Label granularity | Format | License | Direct plug-in cost |
|---|---|---|---|---|---|
| InjecAgent | 1,054 cases | 2 categories (direct harm / data exfiltration) | JSON, tool specs + single-step trajectory | MIT | High — single-step only, coarse labels, own tool set |
| AgentDojo | 629 security test cases | attack-type × domain (4 domains) | Python task objects, executed in-harness | MIT | High — tasks are code-defined against AgentDojo's own simulated Workspace/Slack/Travel/Banking tools |
| ASB | attacks across 16 types (+ 11 defenses) × 10 scenarios | richest of the "classic" set, still a custom taxonomy | Python framework config | MIT | High — 400+ tools, own scenario domains, no `aidr`-taxonomy mapping |
| R-Judge | 569 records | 10 risk types × 5 app categories, 27 scenarios | JSON multi-turn transcripts | **unlicensed** (no LICENSE file — reuse rights unclear) | Medium on format, blocked on licensing without contacting authors |
| AgentHarm | 110 tasks (440 augmented) | 11 harm categories (broad, not technique-level) | JSON/HF dataset | MIT + field-of-use restriction ("AI safety/security purposes only") | Medium format, real license constraint to respect |
| TraceSafe | 1,170 records (13 JSONL files, 90/file) | 12 risk categories + explicit benign baseline; `golden_meta.type` = attacked/pure_benign | JSONL, `role: user\|agent\|tool` full multi-step trajectories, `mutation_category` field | Apache-2.0 (mutations); base traces inherit BFCL's Apache-2.0 | **Best structural match** — schema is close to `TestCase{label, technique_target}` → `Transcript{turns}` → `Verdict`, but built on BFCL tool domains, not this project's 6 real customer-support tools |
| ASSEBench | aggregates AgentHarm/R-Judge/AgentJudge | risk category × outcome (failure/risk/success) | JSON, semantic-annotation + CoT tags | Apache-2.0 | Same underlying data as its sources — same caveats propagate |

The structural obstacle is the same one the project's own preparatory note
(`docs/design/2026-08-19-plan5-dataset-prep-benchmark-esterni.md`) already identified for
InjecAgent/AgentDojo/ASB, and it generalizes to every dataset above, including the newly-found
TraceSafe: **the cost is not in the schema, it is in the content.** `TestCase` only needs a free-text
seed and a label/rationale; it does not care how many tools exist. But none of these datasets'
*transcripts* were produced by this project's actual toy agent calling its actual 6 Python tool
implementations through `build_tool_registry()` — they were produced by different agents against
different (often simulated/emulated) tool surfaces. Importing a transcript wholesale, rather than
just the scenario premise, means either:

1. fabricating a matching SourceLens/tool-registry entry for a tool the toy agent never actually
   runs — exactly the kind of after-the-fact, non-executed distortion the anti-distortion constraints
   already established for the toy tools (static code, decided before seeing detector reaction,
   single source of truth copied into the image at build) are designed to prevent; or
2. rewriting the scenario as a seed and letting the real toy agent generate its own transcript against
   its real tools — which is precisely what Plan 5's hand-authoring already does, using the external
   dataset only as an idea/coverage source, not as a data source.

There is no third option that preserves the project's own executed-not-fabricated guarantee.

---

**Aggiornamento (2026-08-19, stesso giorno, dopo la scrittura di questo report)**: il
design doc di Plan 5 (`docs/design/2026-08-19-plan5-dataset-design.md`) applica la
raccomandazione sotto — `catalog/cases.yaml` ha un `source_type: benchmark_inspired`
dedicato, distinto da `real_incident`/`invented`, per tenere tracciabile quando un caso
nasce da un cross-check con questi progetti invece che da ideazione propria o da un
incidente reale. Quattro voci `real_incident` sono già scritte e verificate (ForcedLeak,
postmark-mcp, PocketOS/Railway). **L'esercizio di copertura vero e proprio è stato
eseguito** (Plan 5a Task 6, 2026-08-20): incrociati i 10 risk type di R-Judge, le 2
categorie di InjecAgent, i 16 attack type di ASB (più 11 difese, 27 in totale
conteggiando entrambi) e le 11 categorie di AgentHarm contro i 14 T-code del vendor —
il catalogo, ormai a 31 voci, era abbastanza popolato per dare segnale. Risultato
completo in `docs/research/2026-08-19-taxonomy-cross-check-findings.md`: **nessun gap
trovato a livello di tecnica/vettore d'attacco** — ogni categoria delle 4 tassonomie
esterne che descrive *come* un agente viene attaccato o indotto a un comportamento
dannoso ha un analogo ragionevole tra i 14 T-code. Un'unica osservazione registrata
come future work, non come gap tecnico: le categorie di R-Judge (3/10) e soprattutto
AgentHarm (9/11) senza analogo classificano per dominio del contenuto/esito dannoso
(es. odio, autolesionismo, terrorismo) — un asse ortogonale alla classificazione per
tecnica dei 14 T-code, non colmabile estendendo quei T-code.

---

## Recommendation

**Plan 5 dataset construction: keep hand-authoring.** No dataset found can be dropped into
`load_dataset()` without either breaking the project's executed-transcript guarantee (option 1 above)
or being reduced to exactly the work Plan 5 already plans to do (option 2). This is not a hedge — it
is a direct consequence of a structural fact verified across eight-plus projects: every existing
dataset's ground truth is coupled to *its own* tool surface and *its own* taxonomy, and none of that
coupling survives a transplant into a different agent running different tools under a different
vendor's technique codes. Use the external projects exactly as the existing prep note already
proposed, now with firmer grounding: **as a coverage checklist**, not a data source. Concretely: walk
R-Judge's 10 risk types, InjecAgent's 2 harm categories, ASB's 16 attack types (plus 11
corresponding defenses), and AgentHarm's 11 harm categories against the catalog's 14 T-codes once
Plan 5's catalog is more complete, looking
specifically for a malicious pattern that shows up in one of theirs but has no analog anywhere in the
14 — that is a real gap-finding exercise their taxonomies are good for, distinct from importing their
data. TraceSafe's *mutation methodology* (structured perturbation of a benign baseline trace into a
labeled attacked variant) is worth revisiting later, not now — it is a plausible way to scale past
40-60 cases once the toy agent's tool surface is stable, but adopting it today would mean building
Plan 5's ground truth on a 12-day-old, 1-star, gated, field-unvalidated dataset — the exact kind of
unverified trust `SPIRIT.md` principle 2 exists to prevent, applied here to a research artifact
instead of a vendor benchmark, but the same discipline.

**The toy-agent/container architecture should not have used an existing harness, and this is not a
close call.** Every established project investigated — AgentDojo, InjecAgent, ASB, AgentHarm,
ToolEmu, AgentBench — solves *agent red-teaming*: attack an agent (optionally wrapped in an in-process
defense), see whether it complies, all inside one harness's process boundary. This project's stated
goal is *detector auditing*: measure whether a structurally separate, independently-shipped product
correctly flags behavior in transcripts it had no hand in generating, without letting that product's
assumptions leak into how the transcripts get made. Those are different problems with different
required shapes. A harness where "defense" is a pluggable in-process component (AgentDojo, ASB) has
no seam at which to insert `aidr` as a black box graded from the outside — its entire evaluation loop
assumes it controls both the attack and the defense. Even the three closest projects found —
R-Judge, ToolEmu, TraceSafe — which do separate "the thing being judged" from "the judge," still use
their *own* built-in judge model as the thing under test, not an arbitrary external product reached
over a network-isolated boundary the way this project's orchestrator reaches `aidr`. This project's
two-container, network-isolated, orchestrator-mediated design is solving specifically for that seam —
it is the one architectural property none of the twelve projects surveyed has, and it is exactly the
property `SPIRIT.md`'s independence requirement needs. Building it from scratch was the correct call,
not an oversight to correct retroactively.

## Sources consulted

- GitHub REST API (`gh api repos/<owner>/<repo>`) for all license/date/star metadata — primary,
  platform-authoritative.
- arXiv abstracts/PDFs fetched directly: 2410.09024 (AgentHarm), 2403.02691 (InjecAgent), 2401.10019
  (R-Judge), 2410.02644 (ASB), 2406.13352 / repo README (AgentDojo), 2309.15817 (ToolEmu), 2308.03688
  (AgentBench), 2604.07223 (TraceSafe), 2607.28685 (validity audit), 2605.16282 (taxonomy/consistency
  survey).
- Project READMEs fetched directly from GitHub raw/blob URLs: AgentDojo, R-Judge, PurpleLlama/
  CybersecurityBenchmarks, GuardBench, AgentAuditor-ASSEBench, AgentDoG, inspect_evals AgentHarm page.
- `huggingface.co/datasets/CyCraftAI/TraceSafe` dataset card for schema/format detail.
- Existing project note `docs/design/2026-08-19-plan5-dataset-prep-benchmark-esterni.md`, reused as
  starting point and extended/re-verified rather than duplicated.
