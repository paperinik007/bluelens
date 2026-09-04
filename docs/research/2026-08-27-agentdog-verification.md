# AgentDoG 1.5 verification against primary sources — is it a defensible second-vendor choice?

Research task, primary sources only (HF API/model cards/`config.json`, GitHub REST API, arXiv paper
HTML/PDF, official project page, Semantic Scholar citation graph). Written to settle a real
discrepancy between this project's own market research
(`docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`, hereafter "the market doc")
and the later design work (`docs/notes/2026-08-26-analisi-integrazione-secondo-vendor.md` and
an operator handoff note from the same day) that picked AgentDoG anyway without engaging the
market doc's own ranking. Dates below are as of 2026-08-27.

## Verdict

**AgentDoG 1.5 is a defensible but weak second-vendor choice, and the market doc's original ranking
holds up under closer primary-source verification — if anything it strengthens.** AgentDoG is a real,
citable, actively-developed academic-lab research artifact (Shanghai Artificial Intelligence
Laboratory, "AI45Lab"/"AI45Research" — the same institution under two consistent, non-conflicting
names, not two different owners), not a product any company sells or has a commercial vehicle around.
It has no independent third-party accuracy evaluation; its accuracy claims rest on its own
self-authored ATBench family plus one external benchmark (R-Judge) it also self-reports scores on. Its
GitHub adoption (687 stars) is real but modest and **its code repository has not been pushed since
2026-06-08** — nearly three months stale as of this writing, which corrects and contradicts the market
doc's carried-over claim of "pushed 2026-08-19" (see §6). Both LlamaFirewall (Meta-backed, 4,365 stars,
pushed yesterday) and Invariant Labs' flagship repo (now rebranded `snyk/agent-scan`, 2,964 stars,
pushed *today*) show materially stronger, more current adoption signals on primary sources checked in
this same pass. The design work's own rationale ("not experimental" / production-readiness) is not
supported by what a primary-source check actually finds: AgentDoG is a research release with no
paying customers, no SLA, no company behind it besides the lab itself, and no independent evaluation —
"experimental" is in some ways a more accurate description of AgentDoG than of the other two
candidates. This does not make auditing AgentDoG worthless — a self-graded, academic, open-weight
detector is a legitimate and interesting audit target, and its architecture (local generative LLM,
0.8B CPU-compatible, taxonomy-rich output) is genuinely the most different from `aidr`'s OpenRouter-API
pipeline of the three reachable candidates, which is a real point in its favor on criterion (a) that
the market doc's original one-line dismissal ("the same audit this project just did") somewhat
undersold. But choosing it over LlamaFirewall or Invariant on "not experimental" grounds specifically
is not supported by the evidence gathered here.

---

## 1. Who actually built/owns AgentDoG 1.5

**Resolved: it is a university-affiliated national AI research lab, not a company, and the two names
in prior docs are not a contradiction.**

- The GitHub organization is `AI45Lab` (org display name field literally reads `"OpenAI45Lab"` — an
  internal naming quirk on GitHub's org profile, not a separate entity; no company/blog/location field
  is set on the org). [VERIFIED: `api.github.com/orgs/AI45Lab`, fetched 2026-08-27] Org created
  2025-01-10, 119 followers, 68 public repos.
- The Hugging Face organization publishing the model weights is `AI45Research` (22 models, 7 datasets,
  1 space, 3 papers, 54 followers, not HF-verified). [VERIFIED: `huggingface.co/api/organizations/AI45Research/overview`]
- The GitHub README's own badge links point to the ModelScope org `Shanghai_AI_Laboratory` for the
  same model collection (`modelscope.cn/collections/Shanghai_AI_Laboratory/AgentDoG15`), and the
  arXiv 1.5 paper's HTML render states the sole listed institutional affiliation is **"Shanghai
  Artificial Intelligence Laboratory."** [VERIFIED: `raw.githubusercontent.com/AI45Lab/AgentDoG/main/README.md`,
  `arxiv.org/html/2605.29801v1`] So: `AI45Lab` (GitHub), `AI45Research` (Hugging Face), and
  `Shanghai_AI_Laboratory` (ModelScope) are three different platform-specific handles for the same
  underlying institution — a national/academic AI research lab in Shanghai, not three different
  organizations. This resolves the inconsistent attribution flagged in the task: "AI45Lab, Shanghai AI
  Lab" and "AI45Research" are consistent, not conflicting.
- Shanghai AI Laboratory itself (per CB Insights company profile, a secondary source used only for
  general orientation, not for any AgentDoG-specific claim) is a large state-linked/academic AI research
  institute, not a startup with commercial AI-security products.
- **No commercial vehicle found.** No pricing page, no "book a demo," no SaaS offering, no company
  website distinct from the lab's own GitHub/HF/project-page presence was found anywhere in this
  research pass. The README does cross-promote an unrelated project ("dot-skill" / `titanwings/colleague-skill`,
  a Discord-linked personal-memory/companion project) at the bottom of the same README file — this is a
  curiosity worth flagging (the same README literally contains promotional badges for a different,
  seemingly unrelated Claude/OpenClaw-integration project) but is not evidence of a commercial vehicle
  for AgentDoG itself. [VERIFIED: raw README fetch, 2026-08-27]

## 2. Real-world adoption signal (AgentDoG 1.5 specifically)

[All figures VERIFIED via `huggingface.co/api/models` and `api.github.com`, fetched 2026-08-27]

**GitHub** (`AI45Lab/AgentDoG`, the single repo covering both 1.0 and 1.5):
- 687 stars, 33 forks, 2 open issues, no license file detected by GitHub's own license API field
  (`"license": null`) despite the README and HF model cards declaring Apache-2.0 (see §5).
- **`pushed_at: 2026-06-08T08:14:09Z`** — this is a hard correction to the market doc, which carried
  forward (without re-verification, explicitly marked as reused) a claim of "682 stars, pushed
  2026-08-19." As of this fetch (2026-08-27), the repo has **not** been pushed in nearly three months.
  Either the earlier "pushed 2026-08-19" figure was mistaken, or the repo saw a force-push/history
  rewrite since then that reset `pushed_at` to an earlier commit's timestamp — either way, the
  "actively maintained" characterization in the market doc's per-candidate detail section for AgentDoG
  is not supported by what this pass finds. Star growth in the same window (682 → 687, +5 stars in
  ~7 days around 2026-08-20, essentially flat since) is also modest.

**Hugging Face downloads/likes**, full org model list (22 models total, AI45Research):
| Model | Downloads (30d) | Likes |
|---|---|---|
| AgentDoG-Qwen3-4B (v1.0, most popular) | 2,099 | 23 |
| AgentDoG1.5-Qwen3.5-4B | 347 | 2 |
| AgentDoG1.5-Qwen3.5-0.8B (the Base variant the design work picked) | 105 | 1 |
| AgentDoG1.5-FG-Qwen3.5-0.8B | 102 | 1 |
| AgentDoG1.5-Unified-Qwen3.5-4B | 41 | 3 |
| AgentDoG1.5-Llama-3.1-8B | 37 | 0 |
| AgentDoG1.5-Qwen3.5-2B | 43 | 0 |
| (remaining 1.0/1.5/SafeWork variants) | 2–26 each | 0–11 each |

These are small numbers in absolute terms — the single most-downloaded model in the whole
organization (2,099/month, the older v1.0 4B model) is roughly what a moderately popular but
non-mainstream open model sees, and the specific model the design work chose (0.8B Base, 105
downloads/month, 1 like) is one of the least-adopted variants in the org's own catalog. No integration
partner, deployment case study, or third-party adopter announcement was found anywhere in this pass.

**Citations** (Semantic Scholar graph API, `arXiv:2605.29801` = the 1.5 paper, `arXiv:2601.18491` = the
1.0 paper, both fetched 2026-08-27):
- AgentDoG 1.5 paper (May 2026): **3 citations**.
- AgentDoG 1.0 paper (January 2026): **26 citations** — a real, non-trivial citation count for a
  7-month-old paper, and the strongest single adoption signal found for the project overall (even
  though it is for the superseded 1.0 architecture, not 1.5). One citing work found by name in this
  pass: "SafeHarness: Lifecycle-Integrated Security Architecture for LLM-based Agent Deployment"
  (Liu et al. 2026). [VERIFIED via Semantic Scholar Graph API `api.semanticscholar.org/graph/v1/paper/arXiv:...`]

**No press coverage, industry recognition, or Gartner/analyst mention was found** for AgentDoG in this
pass — a real contrast with several closed-SaaS candidates in the market doc's Table 1 (Zenity's
Gartner "Cool Vendor," Straiker's $64M Series A) and with LlamaFirewall/Invariant's acquirer-backed
profiles (Meta, Snyk).

## 3. Is AgentDoG marketed/positioned as a product a company could adopt/buy?

**No.** Every primary source checked — the GitHub README, the project page
(`ai45lab.github.io/AgentDoG/v1_5/`), and the arXiv paper — presents AgentDoG as a research artifact:
a technical report, a model zoo, a benchmark family, and (new in 1.5) a described-but-not-packaged
"Online Agent Safety Guardrail" built specifically for "real-world OpenClaw agent deployment." This
last point deserves precision: the README states AgentDoG 1.5 "implements a practical runtime guardrail
system... for real-world OpenClaw agent deployment, supporting online safety monitoring and
intervention in deployed agentic workflows." [VERIFIED: `raw.githubusercontent.com/AI45Lab/AgentDoG/main/README.md`]
This is the closest thing to a "product" claim found — but it describes integration into OpenClaw
(itself referenced in the paper only as an example of a modern agent architecture the taxonomy needed
to be extended to cover, not as a company AI45Lab has a commercial relationship with) rather than
describing a company, pricing, support contract, or SLA of any kind. There is no "contact sales," no
managed/hosted offering, no enterprise tier. This contrasts sharply with every closed-SaaS candidate in
the market doc and even with LlamaFirewall/Invariant, which — while also free and open-source — are
each backed by a company (Meta, Snyk) with clear commercial interests in the surrounding ecosystem
(Llama models, Snyk's AI-security product line) even though the specific tools audited are themselves
free. AgentDoG has no comparable commercial backer at all.

## 4. Benchmark claims and independent evaluation

**Self-authored primary benchmark, with one external benchmark also self-reported on — no
independent/third-party evaluation found.**

- The core benchmark family (ATBench, ATBench-Claw, ATBench-Codex) is authored by the same team as
  AgentDoG itself — the same self-reported conflict-of-interest structure already flagged for `aidr`'s
  Gauntlet. [VERIFIED: arXiv 1.5 paper HTML, `arxiv.org/html/2605.29801v1`]
- The paper also reports results on external, pre-existing benchmarks not authored by this team:
  **R-Judge**, plus citations of AgentHarm, AgentSafetyBench, AgentSecurityBench, AgentDojo, AgentDyn,
  and BFCL (Berkeley Function Calling Leaderboard) as related/comparison benchmarks. On R-Judge, the
  project page reports AgentDoG-1.5-Qwen3.5-4B at 92.2 accuracy / 92.7 F1; on the self-authored ATBench,
  72.4 accuracy / 74.3 F1. [VERIFIED: `ai45lab.github.io/AgentDoG/v1_5/`] This is a genuine partial
  mitigation of the self-grading concern — R-Judge is not the same team's own benchmark — **but the
  R-Judge score is still self-reported by AgentDoG's own authors, not run or verified by an independent
  third party.** No independently-run evaluation of AgentDoG (by anyone outside the author list) was
  found in this pass, either in the paper's own related-work discussion or via web search for
  citations/reviews.
- The paper compares against other **models** (LlamaGuard4-12B, Qwen3-Guard, NemoGuard, ShieldAgent,
  JoySafety, various frontier LLMs including GPT-5.4), not against other **vendor products** in this
  project's sense (LlamaFirewall, Invariant, `aidr` are not mentioned as comparison points anywhere in
  the paper). [VERIFIED: arXiv 1.5 paper HTML fetch, corroborated by the project-page benchmark table]

## 5. License

**Apache-2.0 is declared consistently on every Hugging Face model card checked** (e.g.
`AI45Research/AgentDoG1.5-Qwen3.5-0.8B`: `"license": "apache-2.0"` in `cardData`).
[VERIFIED: `huggingface.co/api/models/AI45Research/AgentDoG1.5-Qwen3.5-0.8B`] Apache-2.0 clearly permits
independent automated evaluation and republishing of results.

**One inconsistency worth flagging**: the GitHub code repository (`AI45Lab/AgentDoG`) itself has **no
LICENSE file at its root**, and GitHub's own license-detection API field returns `null` for it.
[VERIFIED: `api.github.com/repos/AI45Lab/AgentDoG/contents/` directory listing shows no `LICENSE` file;
`"license": null` in the repo metadata] The README's badge area does not carry a license badge either.
This means: the *model weights* have an unambiguous, machine-readable Apache-2.0 declaration on Hugging
Face, but the *code* (data engine, training pipeline, evaluator, guardrail wrapper) in the GitHub repo
has no formal license grant at all — under default copyright law, that code is "all rights reserved"
absent an explicit license, which is a real legal gap for a project this project might want to build an
adapter against or redistribute evaluation code alongside. This should be treated as unresolved rather
than papered over: **only the model weights are confirmed clearly licensed for this project's use; the
surrounding code is not.**

## 6. Sanity-check of the existing docs' technical description (0.8B Base/FG variants)

**Confirmed correct on every point checked — no correction needed here.** Fetched `config.json`
directly from `AI45Research/AgentDoG1.5-Qwen3.5-0.8B` on Hugging Face:

```
"architectures": ["Qwen3_5ForConditionalGeneration"]
"model_type": "qwen3_5"
"vocab_size": 248320 (text_config)
```

No `id2label`, `label2id`, or `num_labels` field anywhere in the config. This is a **generative**
causal-LM architecture, not a classification-head model — confirming the existing docs' correction is
accurate and the `pipeline_tag: text-classification` on the HF model card is metadata/UI hint only, not
a reflection of the actual model class. [VERIFIED: `huggingface.co/AI45Research/AgentDoG1.5-Qwen3.5-0.8B/raw/main/config.json`]

Note: one earlier WebFetch performed during this same research pass, run through the general-purpose
web-summarization tool against the HF model page (not the raw `config.json`), incorrectly reported
"Classification Head: Yes" — apparently inferring this from the `pipeline_tag` metadata rather than the
actual model architecture. This is flagged explicitly here as a caution: **`pipeline_tag` on Hugging
Face model cards is not a reliable signal of actual model architecture** and any future verification of
this or similar models should always check `config.json` directly rather than trusting a page summary.

The two 0.8B variants are confirmed distinct and separately hosted: `AgentDoG1.5-Qwen3.5-0.8B` (Base,
binary safe/unsafe) and `AgentDoG1.5-FG-Qwen3.5-0.8B` (fine-grained, 3D taxonomy only). "Unified" is
confirmed to exist only at 4B (`AgentDoG1.5-Unified-Qwen3.5-4B`). Model card labels list **14 Failure
Mode categories, 10 Risk Consequence categories, 8 Risk Source categories** per one fetched summary of
the model card — this resolves one of the "counts differ across sources (7/12/6 vs 8/14/10)" open
questions noted in the design docs, though this single fetch should still be treated as one data point
rather than independently cross-checked against the paper's own taxonomy table within this pass.

## Comparison table — extending the market doc's own (a)/(b)/(c) methodology

Criteria as defined in the market doc: **(a)** architectural distance from `aidr`'s own pipeline,
**(b)** reachability by a single independent operator without an enterprise budget, **(c)** real-world
adoption that makes an audit publicly valuable. Figures below marked "fresh" were re-verified in this
pass (2026-08-27); AgentDoG figures throughout this file are all fresh.

| Candidate | (a) Architectural distance from `aidr` | (b) Reachability | (c) Adoption (fresh, 2026-08-27) |
|---|---|---|---|
| **AgentDoG 1.5** | High — local generative LLM (0.8B CPU-viable), not an API-cascade classifier pipeline; 3D taxonomy is structurally richer than `aidr`'s | Fully open, Apache-2.0 weights, CPU-runnable at 0.8B (no GPU, no paywall) — but **code repo has no LICENSE file**, and the model this project would run (0.8B Base) is one of the least-downloaded variants in its own catalog (105 downloads/month, 1 like) | **Weakest of the three.** 687 GitHub stars, repo **not pushed since 2026-06-08** (~3 months stale); 1.5 paper has 3 citations (1.0 paper has 26, but that's the superseded architecture); no company, no press, no third-party independent evaluation found; academic-lab-only backing (Shanghai AI Laboratory) |
| **LlamaFirewall** (`meta-llama/PurpleLlama`) | Moderate — combines a BERT-style single-turn classifier with a separate LLM-as-judge multi-step auditor (`AlignmentCheck`/`scan_replay()`), architecturally closer to `aidr`'s "classifier + LLM judge" combination than AgentDoG is, but still a genuinely distinct component design | Fully open, MIT, no paywall; requires an external LLM-judge API call for the multi-step scanner (operational cost, not a vendor gate; OpenRouter feasibility already confirmed in the design docs) | **Strongest.** 4,365 stars (fresh), **pushed yesterday** (2026-08-26 per this fetch's `pushed_at`), backed by Meta — the most unambiguous "actively maintained, well-known" signal of the three |
| **Invariant Labs** (Guardrails + MCP-Scan) | Highest — declarative policy/rule engine over recorded traces, a genuinely different detection paradigm (not a trained classifier at all) | Fully open, Apache-2.0, `pip install`-able, no paywall; requires the auditor to author policies by hand before there is anything to score (a real, different kind of effort than scoring a black-box verdict) | **Strong, with a notable fresh finding**: `invariantlabs-ai/invariant` itself has gone quiet (453 stars, last pushed 2026-01-12 — over 7 months stale). But its companion repo, previously tracked here as `invariantlabs-ai/mcp-scan`, **has been renamed/moved to `snyk/agent-scan`** (confirmed via GitHub's repo-ID redirect) and is now at **2,964 stars, pushed today** (2026-08-27) — i.e., materially more active than the market doc's 2026-08-20 snapshot suggested, now flying under the Snyk brand rather than the Invariant one |

**Net read**: the market doc's original conclusion — that AgentDoG is the weakest of the four reachable
open-source candidates on (a) and (c), with LlamaFirewall strongest on (c) and Invariant strongest on
(a) — is not overturned by this fresh check; if anything the gap has widened, because AgentDoG's repo
has gone stale in the intervening window while LlamaFirewall and Invariant/Snyk's flagship scanner have
both shown fresh, dated activity as of this same day. The one point genuinely in AgentDoG's favor that
this pass surfaces more clearly than the market doc did is architectural distance on the "local
generative model with a rich taxonomy" dimension specifically — a real, different failure mode to test
than either LlamaFirewall's or Invariant's designs — but that alone does not overcome its weak, stale
adoption profile and total absence of independent evaluation or commercial backing.

## Sources consulted

- GitHub REST API (`gh api`/`curl` on `api.github.com`), fetched 2026-08-27: `orgs/AI45Lab`,
  `repos/AI45Lab/AgentDoG` (incl. `contents/` directory listing), `repos/meta-llama/PurpleLlama`,
  `repos/invariantlabs-ai/invariant`, `repos/invariantlabs-ai/mcp-scan` (redirects to
  `repositories/962024783` = `snyk/agent-scan`).
- Hugging Face API/model cards, fetched 2026-08-27: `api/organizations/AI45Research/overview`,
  `api/models?author=AI45Research` (full 22-model listing with downloads/likes),
  `AI45Research/AgentDoG1.5-Qwen3.5-0.8B/raw/main/config.json`,
  `api/models/AI45Research/AgentDoG1.5-Qwen3.5-0.8B` (full model metadata).
- GitHub raw README: `raw.githubusercontent.com/AI45Lab/AgentDoG/main/README.md` (full file, including
  citation/BibTeX block and license-adjacent sections).
- arXiv: `arxiv.org/abs/2605.29801` and `arxiv.org/html/2605.29801v1` (AgentDoG 1.5 paper — HTML render
  used since the raw PDF fetch failed/returned binary garbage on first attempt).
- Project page: `ai45lab.github.io/AgentDoG/v1_5/`.
- Semantic Scholar Graph API (`api.semanticscholar.org/graph/v1/paper/arXiv:2605.29801` and
  `arXiv:2601.18491`), fetched 2026-08-27 after repeated 429 rate-limiting — eventually succeeded.
- WebSearch used only for discovery (locating the above primary URLs) and for confirming no
  independent third-party evaluation or press coverage exists — no claim in this file rests solely on
  a WebSearch AI-generated summary; every substantive claim above is tied to a specific fetched
  primary-source URL.
- Reused without re-verification from the market doc (2026-08-20) for context only, not relied on for
  any AgentDoG-specific claim in this file: the general market-structure findings about the ten
  closed-SaaS candidates.

## Open items not resolved in this pass

- The exact taxonomy category counts (14/10/8 per one model-card fetch) were not independently
  cross-checked against the arXiv paper's own taxonomy table — flagged as a single-source data point,
  not fully verified.
- Semantic Scholar's citation count (3 for the 1.5 paper) reflects that database's indexing only; it is
  not a Google Scholar count and may undercount citations Semantic Scholar hasn't indexed yet, given
  the paper is only ~3 months old as of this writing.
- Whether the missing LICENSE file on the GitHub code repo (as opposed to the HF-hosted model weights)
  is an oversight or a deliberate choice was not determined — no GitHub issue or discussion raising it
  was found in the time available for this pass.
