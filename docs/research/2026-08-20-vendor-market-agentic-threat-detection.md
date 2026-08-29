# Vendor market map: "agentic AI threat detection" products, verified against primary sources

Research task, primary sources only (official vendor sites, docs, GitHub repos/READMEs, GitHub REST
API for repo metadata, official acquirer press releases — never a third-party blog or "top N"
listicle as the source of a vendor's own technical claim). Scope: **vendor products** (open-source or
commercial/SaaS, self-promoting with their own benchmark or marketing claims), not academic
harnesses — those were already covered in
`docs/research/2026-08-19-prior-art-agent-security-harnesses.md` (AgentDojo, InjecAgent, ASB,
AgentHarm, ToolEmu, AgentBench, R-Judge, TraceSafe, AgentAuditor/ASSEBench), reused here rather than
re-verified for the two vendor products it already found (AgentDoG, and `aidr` itself under audit).
Focus is specifically on products that claim to monitor **multi-step agent tool-call trajectories**
and detect malicious/risky behavior across a sequence of actions — single-turn prompt/content
moderation is a related but distinct, adjacent market and is excluded (marked OUT OF FOCUS where
encountered, not omitted).

Dates below are as of 2026-08-20. Many products in this space have been acquired in 2025-2026 by
larger security vendors (Check Point, F5, Palo Alto Networks, Cisco/Splunk, SentinelOne, Snyk) — this
consolidation is itself a market-structure finding, noted per candidate.

> **Verifica successiva e decisione presa (2026-08-27)**: `docs/research/2026-08-27-agentdog-verification.md`
> riverifica su fonti primarie fresche i fatti su AgentDoG, LlamaFirewall e Invariant Labs/Snyk citati
> nella sezione "Updated recommendation (after external research)" più sotto, e corregge un dato
> riportato acriticamente qui sotto (il claim "pushed 2026-08-19" per AgentDoG — al 27 agosto il repo
> risulta fermo dall'8 giugno 2026). **Con l'utente si è deciso il secondo vendor: LlamaFirewall**
> (Meta, MIT, mai acquisito), coerente con la "net recommendation" di questo stesso documento
> (LlamaFirewall come fallback più forte dopo Invariant Labs) e con la riverifica del 27 agosto.
> AgentDoG resta scartato per ora.

> **Addendum 2026-08-29 — verifica di una lista esterna (fonte non tracciabile, stile "AI overview",
> nessuna citazione a fonte primaria) incollata dall'utente.** Tre nomi già presenti come "non
> verificati" in questo file (Arthur, Tigera, Linx Security) sono stati verificati su fonte primaria e
> spostati in Tabella 2 — tutti reali, tutti fuori fuoco (governance/identità/firewall single-turn, non
> detection di traiettoria). Aggiunto **Llama Guard** (Meta) come voce distinta da PromptGuard
> 2/LlamaFirewall, per evitare confusione futura in questo stesso progetto. **Un nome nella lista
> incollata è risultato probabilmente inventato**: "CalypsoAI (ModerShield)" — i prodotti reali
> verificati sono "Moderator", "Vesper Validate" e "CalypsoAI Inference Platform"; nessuna fonte trovata
> per "ModerShield". **Un errore di categorizzazione**: la lista trattava "Prompt Security" e
> "SentinelOne Singularity" come due soluzioni distinte in categorie diverse — SentinelOne ha acquisito
> Prompt Security (annunciato 2025-08-05, chiuso 2025-09-05), fatto già registrato in questo stesso file
> (riga Prompt Security in Tabella 1). **Tre strumenti citati (TruLens, Ragas, Phoenix/Arize) restano
> fuori scope per questo file**: sono strumenti di *quality evaluation* (allucinazioni, pertinenza RAG,
> observability) per un mercato adiacente ma distinto dalla *threat detection* che questo documento
> mappa — non aggiunti a Tabella 2 per non annacquare lo scope dichiarato in testa al file, ma
> registrati qui per trasparenza. Nessuna azione di prodotto richiesta da questa verifica: nessuno dei
> nomi verificati cambia la raccomandazione già presa (LlamaFirewall come secondo vendor).

## Summary

Fourteen vendor candidates verified as genuinely in-focus (real multi-step tool-call trajectory
detection, not just single-turn scanning rebranded as "agentic"). Five candidates verified and
excluded as out-of-focus, with the specific primary-source evidence for exclusion. The market has
consolidated hard: of the fourteen in-focus candidates, nine have been acquired by a larger security
company in the last ~18 months (Lakera→Check Point, CalypsoAI→F5, Protect AI→Palo Alto Networks,
Prompt Security→SentinelOne, Invariant Labs→Snyk, Galileo→Cisco/Splunk, Robust Intelligence→Cisco —
counted once as Cisco AI Defense). Almost none publish a self-reported P/R/F1 benchmark at all — most
publish zero quantitative claims, a handful publish a single unverifiable percentage with no test-set
description (Nightfall AI's "95% precision," CalypsoAI's "97%/95%," Obsidian's "90% over-permissioned"
statistic is about posture, not detection accuracy). This is actually the opposite failure mode from
`aidr`: `aidr` publishes a specific, checkable number (P=1.0, R=0.667, 300 sessions/42 malicious) that
this project can audit; most of this market publishes no number to audit at all, which is arguably a
worse transparency posture, not a better one. Almost every candidate is closed/SaaS, contact-sales-only,
with no self-serve trial — the few open-source, self-hostable exceptions (Invariant Labs, Lasso
Security's gateway, LlamaFirewall, AgentDoG) are exactly the candidates a future independent audit
could actually reach without an enterprise budget.

---

## Table 1 — In-focus candidates (verified multi-step agent trajectory detection)

| Vendor | Product type | What it claims to detect | Self-reported benchmark? | Requires multi-step trajectory? | Maturity / license |
|---|---|---|---|---|---|
| **Lakera** (now Check Point AI Guardrails) | Closed SaaS | Prompt attacks, content violations, data leakage, malicious links, **Agent Behavior Defense** (off-task tool calls, tool allow/deny list) | No P/R/F1; one unmethodologied "91% blocked" claim in a blog post | Yes (tool calls + tool responses in sequence), but "Agent Behavior Defense" is flagged "early access" | Acquired by Check Point (branding live); contact-sales only, no public trial |
| **CalypsoAI** (now F5 AI Guardrails / Inference Defend) | Closed SaaS | Prompt injection, jailbreaks, data exfiltration, policy violations at inference; separate Red-Team/Defend/Observe products | "97% harmful prompts blocked, 95% decision accuracy" — no test set, no methodology disclosed | Partial — "execution traces," but technical depth not disclosed in fetchable pages | Acquired by F5 (closed 2025-09-26, $145.2M); **own domain `calypsoai.com` currently has an expired TLS certificate** — a real red flag on active maintenance of the standalone site |
| **Straiker** | Closed SaaS | Prompt injection, indirect injection, tool misuse, data exposure, multi-step exploit paths, inter-agent manipulation (Discover/Ascend/Defend AI) | No P/R/F1; three unmethodologied stats from its own "STAR Labs" research (28.6% of cataloged MCP tools "dangerous," 91% of attacks silently exfiltrate, 36% lead to RCE) | Yes — Ascend AI explicitly red-teams "multi-step exploit paths" | $64M Series A (2026-06), named customers (Omada Health, Coupa, Amex GBT, EnterpriseDB); contact-sales/demo only, no self-serve |
| **Obsidian Security** | Closed SaaS | MCP tool-call monitoring: which tool, what data returned, on whose behalf; privilege escalation via "maker mode," agent-to-agent chains | No detection P/R; cites a posture stat ("90% of agents over-permissioned") unrelated to detection accuracy | Yes, explicitly — page distinguishes single-call visibility from "action chaining" across a sequence | $85M Series D; named customers (T-Mobile, Databricks, S&P Global, Snowflake); **monitoring/audit-trail only today — runtime enforcement (blocking) is an explicit roadmap item for Q1/Q2 2026, not yet shipped** |
| **Lasso Security** | Hybrid: open-source gateway + closed SaaS | Prompt injection (incl. hidden instructions in tool descriptions), data exfiltration, tool poisoning, "unusual tool call sequences" via an "intent deputy" | None disclosed | Yes — explicitly monitors sequences, not isolated calls | GitHub `lasso-security/mcp-gateway`: [VERIFIED via `gh api`] 385 stars, MIT license, last push 2026-01-22, 12 open issues. Named customers incl. US DHS, Fiverr, eToro; core gateway is self-hostable, advanced platform features are SaaS |
| **Invariant Labs** (now Snyk Labs) | Open source | Declarative security policies over full agent execution traces — tool-call flow rules (e.g. "email sent to unknown address after a DB read"), prompt-injection-in-tool-output detector, MCP-specific: tool poisoning, "MCP rug pulls" | None disclosed in README | Yes, by design — operates on complete message/tool-call histories, not single turns | GitHub `invariantlabs-ai/invariant`: [VERIFIED via `gh api`] 445 stars, Apache-2.0, last push 2026-01-12. GitHub `invariantlabs-ai/mcp-scan`: [VERIFIED via `gh api`] 2,931 stars, Apache-2.0, last push 2026-08-20 (same day as this research). Acquired by Snyk (2025-06-24), ETH Zurich spin-off |
| **Galileo** (now Splunk Agent Observability, Cisco) | Closed SaaS | Primarily an eval/observability platform; security-relevant metrics include prompt injection (trained against "full OWASP injection taxonomy," incl. indirect injection from poisoned documents) and "Tool Misuse" mapped to OWASP Agentic ASI02 | None disclosed for the security metrics specifically (other product areas publish eval-model accuracy claims, not detection P/R) | Partial — security evals reference agent "actions, tool access, and escalation paths," but the primary product framing is quality/observability (hallucination etc.), not adversarial detection | Acquired by Cisco, closed 2026-05-22, folded into Splunk Observability as of 2026-08-07 for new customers; contact-sales with a "get started free" claim, no verifiable technical detail on the free tier's scope |
| **HiddenLayer** | Closed SaaS | "Prompt injections, malicious tool calls, data exfiltration, and cascading attack chains unique to autonomous agents" (Agentic Runtime Security) | None disclosed | Yes — "session reconstruction" and "continuous agent behavior" language implies trajectory-level analysis, though no technical detail published | 30+ patents claimed, named customers (IBM, GitLab, Cohere per homepage logos; AstraZeneca named in a testimonial); contact-sales only |
| **Zenity (AIDR)** | Closed SaaS | Prompt injection (direct/indirect), data exfiltration, unauthorized permission changes, agent-to-agent misuse, memory poisoning, tool misuse — explicitly mapped to **OWASP LLM Top 10 and MITRE ATLAS** | None disclosed (only qualitative claims: "fewer false alarms") | Yes, explicitly — "the signal that matters often only shows up when the whole sequence is read together" | Gartner "Cool Vendor in Agentic AI TRiSM" (2025) and "Company to Beat in AI Agent Governance"; contact-sales only, no self-serve. **Note**: Zenity's product is literally named "AIDR" (AI Detection and Response) — an unrelated product from an unrelated company, not to be confused with `aidr` (FareedKhan-dev), the tool under audit in this project |
| **Prompt Security** (now part of SentinelOne Singularity) | Closed SaaS | MCP Gateway: risk-scores >13,000 known MCP servers, inspects every call/prompt-template/response, enforces allow/block/filter/redact; prompt injection, jailbreaks, data leaks, "Shadow AI" | None disclosed | Partial — gateway inspects every call and enforces per-server policy, but no page fetched confirms cross-call sequence analysis specifically (as opposed to per-call policy enforcement) | Acquired by SentinelOne ($250M, closed 2025); `prompt.security` still live as a standalone branded site ("Prompt Security \| From SentinelOne"), not redirected; contact-sales only |
| **Protect AI** (now Palo Alto Networks Prisma AIRS) | Closed SaaS (+ formerly open-source tools, now archived) | Agent identity verification, "Multi-turn Attack Support" (added Feb 2026), prompt injection, data leaks, model tampering, deserialization attacks | None disclosed | Yes — "Multi-turn Attack Support" and "Red Teaming for Multi-Agent Systems" explicitly named as Feb 2026 features | `protectai.com` [VERIFIED] 301-redirects to `paloaltonetworks.com/ai-security/prisma-airs` — the original brand no longer resolves standalone. Its flagship open-source tool `protectai/llm-guard` [VERIFIED via `gh api`]: 3,201 stars, MIT, **archived** as of last push 2026-07-08 — and llm-guard itself was always single-turn (input/output scanning), not agentic. Contact-sales only for Prisma AIRS |
| **Cisco AI Defense** (absorbs Robust Intelligence) | Closed SaaS | Agent-specific threats named in Cisco's Feb 2026 announcement: memory poisoning, tool misuse, privilege escalation, intent hijacking, deceptive agent behavior; MCP traffic runtime protection ("Tool Exploitation guardrail") | None disclosed in any fetched page (technical data sheet at cisco.com returned HTTP 403, not independently fetchable) | Yes, per the announcement language, but the one page that loaded (a Cisco blog post) only described one detector ("Tool Exploitation") in any detail | Robust Intelligence fully absorbed — no standalone RI product/site found; acquired 2024, "Robust Intelligence" name now only appears historically. Ships an integration with NVIDIA NeMo Guardrails (open-source) as a developer path. Contact-sales only ("schedule time with an expert") |
| **LlamaFirewall** (Meta, part of Purple Llama) | Open source | `scan_replay()` analyzes "entire conversation traces... across a sequence of messages" for misalignment that "might only become apparent over multiple interactions"; **AlignmentCheck** (chain-of-thought auditing for agent goal hijacking), PromptGuard 2 (BERT classifier, single-turn), CodeShield (generated-code static analysis) | Referenced in an associated paper ("LlamaFirewall: An open source guardrail system for building secure AI agents") but no P/R numbers found in the fetched README itself | Yes, explicitly — `scan_replay()` is a dedicated multi-step trajectory API distinct from the single-turn scanners in the same package | MIT license, part of `meta-llama/PurpleLlama` — the parent repo [VERIFIED via `gh api`, from the 2026-08-19 prior-art research] has 4,358 stars and was pushed 2026-08-18 (actively maintained); free, fully self-hostable, no paywall |
| **AgentDoG** (AI45Lab, Shanghai AI Lab) | Open source (+ itself a "vendor" — see caveat) | Runtime guardrail model graded against its own ATBench/ATBench-Claw/ATBench-Codex benchmark family, claiming competitive accuracy/P/R/F1 against larger frontier models | **Yes** — the only in-focus candidate here that publishes its own P/R/F1, but self-reported against its own benchmark (same conflict-of-interest structure this project already refuses to trust for `aidr`'s Gauntlet) | Yes — designed as an agent-safety-alignment framework for runtime deployment | [VERIFIED, reused from `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`] Apache-2.0, 682 stars, pushed 2026-08-19; free, self-hostable, no paywall — the single most "reachable" candidate on this table alongside Invariant and LlamaFirewall |

## Table 2 — Out-of-focus candidates (found, verified, explicitly excluded)

| Candidate | Why excluded |
|---|---|
| **NeMo Guardrails** (NVIDIA) | [VERIFIED: `github.com/NVIDIA/NeMo-Guardrails` README] It is a **rails configuration framework** (Colang DSL), not a trained detector — developers hand-write input/dialog/retrieval/execution/output rails. It does have "Execution rails" wrapping tool input/output, but per-call, not as a sequence/trajectory-level analysis; no autonomous multi-step threat detection of its own. Apache-2.0. Cisco AI Defense (in Table 1) references integrating with it as a developer path, which underlines that NeMo Guardrails itself is infrastructure, not a shipped detector product |
| **Guardrails AI** (`guardrails-ai/guardrails`) | [VERIFIED: GitHub README] Explicitly single-turn: "Input/Output Guards" wrap one LLM call at a time (validators like `RegexMatch`, `CompetitorCheck`, `ToxicLanguage`, via Guardrails Hub). No concept of an agent trajectory or tool-call sequence anywhere in the README. It does run a "Guardrails Index" benchmark comparing 24 different guardrail products/models — a real, useful third-party-style benchmark artifact, but for single-turn content-moderation-class guardrails, not agent trajectories; not directly relevant to this project's scope. Apache-2.0 |
| **Kovrr** | [VERIFIED: `kovrr.com/blog-post/monitoring-ai-agent-behavior-in-production`] Not a detector at all — a cyber-risk-quantification/governance platform that ingests *other tools'* monitoring telemetry and turns it into financial-exposure and compliance reporting for boards. Explicitly frames itself as "a governance layer on top of" agent monitoring, not the monitoring/detection itself |
| **`protectai/llm-guard`** (as a standalone artifact, distinct from Protect AI/Prisma AIRS the company) | [VERIFIED via `gh api`] Always single-turn (LLM input/output text scanning), and now **archived** (no longer maintained) as of last push 2026-07-08 despite 3,201 stars — a real, verifiable example of a well-adopted open-source security tool being sunset post-acquisition |
| **`akasecurity/ai-tc`** | [VERIFIED via `gh api`] Real, actively pushed (2026-08-20, same day), Apache-2.0, "every prompt and tool call is scanned before it runs" — plausibly in-focus by description, but only 10 GitHub stars and no docs/site beyond the README found; too small and too early to verify any substantive claim beyond the one-line repo description. Noted here rather than silently dropped, per this project's own disclosure principle, but not given a full card |
| **Llama Guard** (Meta) | [VERIFIED, 2026-08-29 addendum: `ai.meta.com/research/publications/llamafirewall-an-open-source-guardrail-system-for-building-secure-ai-agents/`, cross-vendor comparison sources] A **separate Meta product from PromptGuard 2/LlamaFirewall, easily confused with them** — worth registering explicitly since this project already integrates LlamaFirewall. Llama Guard is a general-purpose input/output **content-safety classifier** (current version, Llama Guard 4, a 12B multimodal model) trained to flag unsafe content categories (violence, hate speech, etc.), not a jailbreak/prompt-injection specialist (that is PromptGuard 2's job) and not a trajectory/sequence analyzer (that is AlignmentCheck's job within LlamaFirewall). Single-turn, one input/output pair at a time — no multi-step trajectory claim found anywhere |
| **Arthur** (Arthur Shield + Agent Discovery & Governance) | [VERIFIED, 2026-08-29 addendum: `arthur.ai/product/shield` fetched directly; `arthur.ai/blog/arthur-launches-agent-discovery-governance-on-google-cloud-marketplace` and related Arthur blog posts via search] **Arthur Shield** ("the first firewall for LLMs") is confirmed real, but the fetched product page explicitly describes it as sitting "between the application layer and the deployment layer to validate user prompts and model responses **on two endpoints**" — single-turn, no trajectory/session-level language found. No P/R/F1 published. Arthur's newer **Agent Discovery & Governance** platform (launched Dec 2025, on Google Cloud Marketplace since Jan 2026) is agent *inventory and access governance* (discover which agents run where, apply governance controls) — closer to Kovrr's already-excluded "governance layer" category than to trajectory-level attack detection; "granular behavior analysis" is claimed but not described with any trajectory-specific mechanism in the fetched sources |
| **Tigera (Lynx)** | [VERIFIED, 2026-08-29 addendum: `tigera.io/tigera-products/lynx/`, `tigera.io/news/tigera-launches-lynx-a-unified-control-plane-for-kubernetes-native-ai-agents/`, via search] Real product, GA'd 2026 (per `helpnetsecurity.com`, announced 2026-06-17). Kubernetes-native **control plane for authenticating, authorizing, and auditing** agent-to-agent/agent-to-tool/agent-to-LLM calls via eBPF discovery, cryptographic identities, and Cedar-policy default-deny enforcement. This is **access-control/authorization infrastructure, not content/trajectory threat detection** — it decides whether a call is *permitted*, not whether a permitted sequence of actions is *malicious in substance* the way Invariant's policy engine or LlamaFirewall's AlignmentCheck do. Different problem than this project's threat model |
| **Linx Security** | [VERIFIED, 2026-08-29 addendum: `linx.security/solutions/agentic-identity-governance`, `prnewswire.com/news-releases/linx-security-delivers-the-first-contextual-intelligence-ai-agent-for-enterprise-identity-governance-302550182.html`, via search] Real product ("Linx AI-Agent", "Agentic Access Control" GA'd 2026-06). **Identity governance for human/non-human/agentic identities** — discovers which agents exist, who has access to them, inspects MCP tool calls for allow/block at the authorization layer. Same category as Tigera Lynx above: identity/access governance, not content-level malicious-trajectory detection |

**Not independently verified (found only via secondary "top N" listicle articles, explicitly not treated as verified in this file):** WitnessAI, NeuralTrust, Aim Security (Cato Networks), AccuKnox, Orca Security's AI-agent coverage. These names surfaced repeatedly in vendor-comparison blog posts but were not fetched from each vendor's own primary source within this research pass. Listing them here is a scope disclosure, not a claim about what they do — a future pass would need to verify each against its own site/repo before it could appear in Table 1 or 2. **Arthur, Tigera (Lynx), and Linx Security were verified against primary sources in the 2026-08-29 addendum below and moved to Table 2.**

---

## Per-candidate detail

### Lakera / Check Point AI Guardrails

[VERIFIED: `docs.lakera.ai/docs/agent-security`, `docs.lakera.ai/docs/defenses`]. Five guardrail
components: Prompt Defense, Content Moderation, Data Leakage Prevention, Malicious Links, and **Agent
Behavior Defense** — the only one that is genuinely trajectory-relevant, with two named detectors: an
**Off-Task Action Detector** ("detects tool calls inconsistent with the user's intent") and a **Tool
Allow/Deny List** ("controls which tools an agent may call at runtime"). The docs describe screening
"prompts, tool calls, tool responses, and actions that flow through an agent as it operates," which
implies per-step screening across a session rather than a single input/output pair, but the fetched
pages do not describe any explicit cross-step pattern analysis (e.g., "action A followed by action B is
suspicious") the way Invariant's policy engine or Obsidian's chain analysis do. Branding on the docs
site reads "Check Point AI Guardrails," confirming the earlier Lakera→Check Point acquisition; the
product is presented as "early access" for the agent-security surface specifically. No benchmark
numbers of any kind on the fetched pages. Closed SaaS, no visible free tier.

### CalypsoAI / F5 AI Guardrails (Inference Defend)

[VERIFIED: `f5.com/company/blog/outcome-analysis`; F5 press release `f5.com/company/news/press-releases/f5-to-acquire-calypsoai-to-bring-advanced-ai-guardrails-to-large-enterprises`]. F5 announced intent
2025-09-11 and closed the $145.2M acquisition 2025-09-26. CalypsoAI's three components — Red-Team
(agentic adversarial testing), Defend (real-time protection), Observe (audit/traceability) — are now
sold as "F5 AI Guardrails"/"Inference Defend." The only quantitative claim found, on F5's own blog, is
"blocking 97% of harmful prompts with 95% decision accuracy" — **no test set, no methodology, no
baseline comparison disclosed**, making it unverifiable as stated. Notably, **`calypsoai.com` itself
currently returns a TLS certificate-expired error** on direct fetch — the original vendor's own site is
presently broken from a basic connectivity standpoint, a concrete (if minor) signal of how quickly a
standalone identity decays post-acquisition. Contact-sales only.

### Straiker

[VERIFIED: `straiker.ai/`, `straiker.ai/blog/top-agentic-ai-security-platforms`]. Three products:
Discover AI (agent/MCP inventory), Ascend AI ("AI red teaming engine for agentic failure modes...
multi-step exploit paths"), Defend AI (runtime blocking of "tool manipulation" in real time). Named
threat categories: prompt injection, indirect prompt injection, tool misuse, data exposure, rogue
agent behavior, unsafe tool calls, unauthorized actions, inter-agent manipulation. Three research
statistics cited from its own "STAR Labs" team (28.6% of cataloged MCP tools "dangerous on their
face"; 91% of attacks on productivity agents result in silent exfiltration; 36% of successful attacks
on coding agents achieve RCE) — presented without disclosed sample size or methodology, so treat as
marketing statistics, not a benchmark. $64M Series A closed 2026-06. Real named enterprise customers
with testimonials (Omada Health, Coupa, American Express Global Business Travel, EnterpriseDB,
Automation Anywhere) plus trust-logo-only mentions (DirecTV, Comcast, Fortinet, Deloitte, Snowflake).
No GitHub presence found — fully closed SaaS, "Book a Demo"/"free AI risk assessment" only, no
self-serve trial.

### Obsidian Security

[VERIFIED: `obsidiansecurity.com/academy/mcp-tool-call-monitoring`, `obsidiansecurity.com/`]. The
clearest primary-source statement in this whole survey of the monitoring-vs-enforcement distinction:
Obsidian explicitly says "Monitoring is the prerequisite. It is not the destination" and states that
runtime enforcement (blocking a tool call before it completes) is **on the roadmap, not shipped** —
targeting late Q1 2026 for Copilot and Q2 2026 for additional platforms. Today it captures four data
points per MCP tool call (tool invoked, input parameters, data returned, invoking identity) and
explicitly distinguishes single-call visibility from "action chaining" (multi-call sequences), which
it says is invisible without per-call records in sequence — this is a genuine, if currently
detection-only (not blocking), trajectory-level capability. Named threat concepts: "maker mode"
privilege escalation (agents invoked under creator credentials bypassing IAM), "machine insider risk,"
agent-to-agent chains crossing permission boundaries. $85M Series D; named customers T-Mobile,
Databricks, S&P Global, Snowflake, BigCommerce, Seagate, with CISO-level testimonials from several.
Contact-sales with a "Free Trial" button, though trial scope/duration is not disclosed on the fetched
pages.

### Lasso Security

[VERIFIED: `lasso.security/use-cases/mcp`, `lasso.security/`, `github.com/lasso-security/mcp-gateway`
via `gh api`]. The **intent deputy** concept is the most concrete trajectory-relevant mechanism found
in this whole survey: it "evaluates whether a tool call aligns with the agent's stated objective and
flags anomalous requests that may indicate compromise or misuse," combined with monitoring of "unusual
tool call sequences." Named threats: prompt injection (including hidden instructions inside tool
descriptions — tool poisoning), data exfiltration (PII/API keys/credentials via tool calls), behavioral
anomalies. Uniquely among the closed-SaaS-dominated field, Lasso ships a genuinely **open-source,
self-hostable MCP gateway** (`lasso-security/mcp-gateway`, MIT, 385 stars, last push 2026-01-22, 12
open issues) as the foundation, with discovery/policy/compliance-reporting features reserved for the
paid platform on top. Real named customers spanning public sector and enterprise: US Department of
Homeland Security, Fiverr, eToro, Optibus, Delek US, Telit, Kaltura, Nayax. Gartner "Cool Vendor 2024."
No published benchmark numbers.

### Invariant Labs (now Snyk Labs)

[VERIFIED: `github.com/invariantlabs-ai/invariant` README and `gh api`, `github.com/invariantlabs-ai/mcp-scan` via `gh api`, Snyk press release `snyk.io/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation/`]. An ETH Zurich spin-off (co-founded 2024 by
Martin Vechev and Florian Tramèr) acquired by Snyk on 2025-06-24, less than a year after founding.
Architecturally distinct from every other candidate on this list: **Guardrails** is a declarative
policy engine over recorded agent traces, not a trained classifier — its README example rule pattern
`(call: ToolCall) -> (call2: ToolCall)` matches flows *between* tool calls explicitly, and a built-in
detector flags prompt injection appearing in tool output before a subsequent call executes. It
requires actual multi-step agent execution traces (message histories with tool calls and outputs) as
input — analysis is post-hoc over a full trace, not speculative. **MCP-Scan**, the more adopted of the
two repos (2,931 stars, Apache-2.0, pushed same day as this research, 2026-08-20), targets MCP-specific
threats: tool poisoning and "MCP rug pulls" (a server changing its declared tool behavior after initial
trust is established). No benchmark numbers published in either README. Fully open-source, Apache-2.0,
genuinely self-hostable by a single independent operator — one of only three candidates in this survey
(alongside LlamaFirewall and AgentDoG) with zero paywall.

### Galileo (now Splunk Agent Observability, Cisco)

[VERIFIED: `galileo.ai/`, `v2docs.galileo.ai/concepts/metrics/safety-and-compliance/prompt-injection`,
Cisco press release `blogs.cisco.com/news/cisco-announces-the-intent-to-acquire-galileo`]. Cisco
announced intent 2026-04-09, closed 2026-05-22; as of 2026-08-07 the product is "Splunk Agent
Observability" for customers onboarding after that date (the `galileo.ai` domain itself still shows no
Cisco/Splunk branding as of this fetch, suggesting a staged rebrand). Primarily an **evaluation/quality
observability platform** (20+ metrics including hallucination, cost, latency) with security-relevant
metrics layered on: a Prompt Injection metric explicitly "trained against the full OWASP injection
taxonomy" including indirect injection from poisoned retrieved documents, and Tool Misuse mapped to
**OWASP Top 10 for Agentic Applications, ASI02** (their own framing: "perhaps the most uniquely
agentic threat in the OWASP taxonomy"). This OWASP-Agentic alignment is the most structured public
taxonomy reference found among the closed-SaaS candidates. No detection-specific P/R/F1 disclosed —
other Galileo product areas (Luna-2 eval models) publish accuracy claims for evaluation quality, not
for adversarial-detection precision/recall. Contact-sales with a "Get Started for Free" button whose
scope is not verifiable from the fetched pages.

### HiddenLayer

[VERIFIED: `hiddenlayer.com/news/hiddenlayer-unveils-new-agentic-runtime-security-capabilities-for-securing-autonomous-ai-execution`, `hiddenlayer.com/`]. Names four threat categories for its
"Agentic Runtime Security" capability: prompt injections, malicious tool calls, data exfiltration, and
"cascading attack chains unique to autonomous agents." The phrase "session reconstruction" plus
"continuous agent behavior" monitoring implies trajectory-level analysis, but the fetched announcement
does not describe the actual detection mechanism (rule-based, trained classifier, or LLM judge) at any
technical depth — it reads as a feature announcement, not documentation. 30+ patents claimed; named
customer logos include IBM, GitLab, Cohere, NFL; one attributed testimonial (AstraZeneca). No benchmark
numbers of any kind. Contact-sales only ("contact sales@hiddenlayer.com to schedule a demo").

### Zenity (AIDR)

[VERIFIED: `zenity.io/platform/ai-security-platform/aidr`, `zenity.io/`]. The most structured public
taxonomy found among the closed-SaaS-only candidates: threats explicitly mapped to **both OWASP LLM
Top 10 and MITRE ATLAS**, naming prompt injection (direct/indirect), data exfiltration, unauthorized
permission changes, agent-to-agent activity misuse, memory poisoning, and tool misuse/unauthorized API
calls. The clearest first-person statement of *why* trajectory-level analysis matters found in this
survey: "AI agents don't operate that way; they chain tool calls, retrievals, and actions together, and
the signal that matters often only shows up when the whole sequence is read together." No P/R/F1
disclosed — only qualitative claims ("fewer false alarms," catching "paraphrased, multi-step" attacks
"pattern matching alone would miss"). Gartner "Cool Vendor in Agentic AI TRiSM" (2025) and "Company to
Beat in AI Agent Governance" are the maturity signals found (no funding round or named customer
disclosed on the fetched pages — case studies are anonymized). Contact-sales only, no self-serve.
**Naming collision worth flagging explicitly**: Zenity's product is literally branded "AIDR" (AI
Detection and Response). This is an entirely unrelated company and product from `aidr`
(`FareedKhan-dev/agentic-threat-detection`), the tool under audit elsewhere in this project — the
lowercase/uppercase and the underlying products have nothing to do with each other; noted here only to
prevent future confusion in this project's own cross-references.

### Prompt Security (now part of SentinelOne Singularity)

[VERIFIED: `sentinelone.com/blog/a-new-chapter-for-ai-and-cybersecurity-sentinelone-acquires-prompt-security/`, `prompt.security/`, `prompt.security/solutions/agentic-ai-security-and-governance`].
SentinelOne's acquisition (~$250M) closed 2025; unlike Protect AI's domain, `prompt.security` **remains
live as its own standalone branded site** ("Prompt Security | From SentinelOne") rather than
redirecting outright. Its **MCP Gateway** sits between AI applications and "more than 13,000 known MCP
servers," inspecting every call/prompt-template/response and assigning each server a dynamic risk score
with allow/block/filter/redact enforcement. Named threats: prompt injection, jailbreak attempts,
malicious output manipulation, prompt leaks, unauthorized "Shadow AI" usage, sensitive data leakage.
The fetched pages describe strong **per-call** inspection and per-server risk scoring but do not
explicitly confirm cross-call sequence analysis the way Invariant, Obsidian, or Lasso's pages do —
treat the trajectory-level claim as partially verified. No benchmark numbers. Contact-sales only.

### Protect AI (now Palo Alto Networks Prisma AIRS)

[VERIFIED: `protectai.com/` → 301 redirect to `paloaltonetworks.com/ai-security/prisma-airs`;
`github.com/protectai/llm-guard` via `gh api`]. Palo Alto Networks completed the acquisition
2025-07-22. **The original `protectai.com` domain no longer resolves to a standalone Protect AI
page at all — it hard-redirects (HTTP 301) straight into Palo Alto's Prisma AIRS product page**, the
most complete brand absorption found in this survey (contrast with Prompt Security, which still keeps
its own domain live). Prisma AIRS's fetched page names "Multi-turn Attack Support" as a February 2026
addition plus "Red Teaming for Multi-Agent Systems," alongside prompt injection, data leaks, model
tampering, deserialization attacks, and a broader eight-category toxicity classifier (as of Feb 2026).
No benchmark numbers found. Protect AI's flagship open-source project, **`protectai/llm-guard`**
("The Security Toolkit for LLM Interactions," MIT, 3,201 stars), is now **archived** (last push
2026-07-08) — a concrete, verifiable case of a well-adopted open-source security tool being sunset
after its maintainer's acquisition. llm-guard itself was always single-turn input/output scanning, not
agentic, so its sunset does not remove trajectory-level capability from the vendor's current offering
— but it does remove the one artifact of Protect AI's lineage that was ever independently auditable by
a third party without a Palo Alto Networks contract. Contact-sales only for Prisma AIRS.

### Cisco AI Defense (absorbs Robust Intelligence)

[VERIFIED: `blogs.cisco.com/ai/security-for-the-agentic-era-cisco-ai-defense-breaks-new-ground`,
`cisco.com/site/us/en/products/security/ai-defense/robust-intelligence-is-part-of-cisco/index.html`
via search-result confirmation; direct fetch of `cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-ds.html` and `cisco.com/site/us/en/products/security/ai-defense/ai-runtime/index.html` **both returned HTTP 403 and could not be independently fetched** — flagged
explicitly rather than relying on a secondary source for their content]. Robust Intelligence
(acquired by Cisco, announced 2024-08-26, closed ~September/October 2024) is now fully absorbed —
no standalone Robust Intelligence product or site was found; the name survives only in a "Robust
Intelligence is part of Cisco" landing page and historical press coverage. Cisco's own February 2026
newsroom announcement (found via search, not independently fetched) names agent-specific threats:
memory poisoning, tool misuse, privilege escalation, intent hijacking, deceptive agent behavior, and
runtime protection extended to MCP traffic. The one Cisco blog post that *was* fetchable describes
exactly one detector in any technical detail — a "Tool Exploitation guardrail" preventing "adversaries
from hijacking connected tools to steal sensitive data." Notably, this same post says Cisco AI Defense
ships a "developer-ready integration with NVIDIA NeMo Guardrails' open source framework" — meaning
Cisco explicitly treats NeMo Guardrails (Table 2, out-of-focus as a detector) as complementary
infrastructure rather than a competing product, which corroborates this survey's own classification of
NeMo Guardrails as a configuration framework rather than a detector. No benchmark numbers found.
Contact-sales only.

### LlamaFirewall (Meta, part of Purple Llama)

[VERIFIED: `github.com/meta-llama/PurpleLlama/tree/main/LlamaFirewall` README; parent-repo stars/date
reused from the 2026-08-19 prior-art research, itself `gh api`-verified]. The most architecturally
explicit multi-step capability found in the entire survey: a dedicated `scan_replay()` function that
"analyzes entire conversation traces to detect potential security issues across a sequence of
messages," built specifically to catch "misalignment or compromised behavior that might only become
apparent over multiple interactions" — distinct from the package's own single-turn scanners.
Components: **PromptGuard 2** (BERT-style classifier, single-turn prompt injection), **AlignmentCheck**
(chain-of-thought auditing for agent goal hijacking/misalignment — the multi-step-aware piece),
**CodeShield** (static analysis of LLM-generated code), plus regex/custom scanners. A companion paper
("LlamaFirewall: An open source guardrail system for building secure AI agents") is referenced as
containing evaluation results, but no P/R numbers appear in the README itself — not verified as a
self-reported benchmark within this pass. MIT license, part of `meta-llama/PurpleLlama` (4,358 stars,
pushed 2026-08-18 per the prior-art research, i.e. actively maintained the day before this research).
Fully free, fully self-hostable — no paywall, no SaaS tier, no contact-sales gate of any kind.

### AgentDoG (AI45Lab, Shanghai AI Lab)

[VERIFIED, reused without re-verification from `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`, itself primary-source-checked one day before this file]. Included here for
completeness since it is unambiguously a **vendor** product (not an academic harness) that fits this
file's scope exactly, even though the prior research already flagged the structural problem: AgentDoG
is simultaneously a detector deployable as a runtime guardrail *and* the benchmark family (ATBench /
ATBench-Claw / ATBench-Codex) it grades itself against — the same self-reported conflict-of-interest
pattern this project already refuses to accept at face value for `aidr`'s own Gauntlet. Apache-2.0, 682
stars, pushed 2026-08-19 (actively maintained), free and self-hostable. It is the only in-focus
candidate on Table 1 that publishes an actual self-reported P/R/F1-style number — which makes it, on
paper, the most "auditable-in-principle" candidate of the entire market, precisely because its claim is
falsifiable rather than absent.

---

## Suitability for the Fase 1 harness (verified 2026-08-26)

After the first full run (31/31 cases, metriche intento-vs-effetto pubblicate), the four
open-source, self-hostable candidates were re-verified against the actual harness
requirements. The harness needs:

1. **Input**: a multi-turn agent transcript (JSON with tool calls and results)
2. **Output**: a verdict (malicious/benign, confidence, technique/category)
3. **Self-hostable**: `pip install` or container, no GPU, no mandatory external API key
4. **Taxonomy**: a declared set of attack techniques (to map 12 techniques of the dataset)

### Suitability table

| Candidate | Input | Output | Self-hostable? | Taxonomy? | Overall fit |
|---|---|---|---|---|---|
| **Invariant Labs** | Messages list (`policy.analyze`), exact match | `AnalysisResult` with errors — no label/confidence/technique | ✅ `pip install invariant-ai` | No — rule engine, user writes policies | ⚠️ Rule engine, not a detector |
| **LlamaFirewall** | `Trace` via `scan_replay()`, multi-turn | `ScanResult(decision=ALLOW/BLOCK, reason, score)` | ✅ `pip install llamafirewall`; ❌ AlignmentCheck requires Together API key | ✅ Scanner types: PROMPT_GUARD, AGENT_ALIGNMENT, CODE_SHIELD | ✅ Best fit |
| **AgentDoG** | Agent trajectory JSON (user/agent/environment) | Fine-grained diagnosis (3D taxonomy) | ❌ GPU + model serving (4B-8B params) | ✅ Three-dimensional taxonomy | ❌ GPU needed |
| **Lasso Security** | MCP traffic only | N/A (gateway, not detector) | ✅ `pip install mcp-gateway` | N/A | ❌ Not a detector |

### Detailed per-candidate analysis

#### Invariant Labs (`invariantlabs-ai/invariant`)

- **Input**: `policy.analyze(messages)` where `messages` is a list of dicts with `role`,
  `content`, `tool_calls` — directly compatible with our transcript format (see README
  example tracing `get_website` → `send_email`).
- **Output**: `AnalysisResult` with an `errors` list — rule engine that fires named rules.
  No confidence, no label, no technique category. The rule name comes from the author's
  definition, not from a vendor taxonomy.
- **Taxonomy**: None. The vendor provides the framework and built-in detectors (prompt
  injection, phishing), but the detection logic is user-written policies. Using Invariant
  would test *our* rules, not the vendor's detection.
- **Containerizability**: ✅ `pip install invariant-ai` (0.3.5). No GPU, no API key.
- **Adapter effort**: high. Need to write ~14 policies (one per technique), which is a
  separate design effort. Output format needs mapping from errors to verdict.

**Assessment**: architecturally interesting but a poor fit for a quick second-vendor test.
The question "does a human-written policy language catch attacks its author didn't think
to write a rule for" is a different research question from "does this trained detector
catch attacks." Worth a future phase, not for immediate validation.

#### LlamaFirewall (`meta-llama/PurpleLlama`, `llama_firewall`)

- **Input**: `scan_replay(trace: list[UserMessage|AssistantMessage])` — the `Trace` is
  exactly a multi-turn conversation. The README example shows a 4-turn booking trace.
  AssistantMessage can include `tool_calls` in OpenAI-compatible format.
- **Output**: `ScanResult(decision=ALLOW|BLOCK, reason=str, score=float)`. The `reason`
  names the scanner that fired (e.g. "prompt_guard", "alignment_check"). The `score`
  is confidence (0.0–1.0).
- **Taxonomy**: ScannerType enum: `PROMPT_GUARD` (injection), `AGENT_ALIGNMENT` (goal
  hijacking, indirect injection), `CODE_SHIELD` (code security). Multi-turn via
  `AGENT_ALIGNMENT` only.
- **Containerizability**: ✅ `pip install llamafirewall`. PromptGuard is a BERT classifier
  (lightweight, no GPU). **But**: AlignmentCheck requires `TOGETHER_API_KEY` (external API
  call to Together AI for LLM-as-judge). This is a real limitation.
- **Adapter effort**: medium. Input format is close to ours. Output is a verdict
  (ALLOW/BLOCK → benign/malicious, score → confidence, reason → technique). Technique
  mapping is coarse (3 scanner types vs. 14 T0001–T0014).

**Assessment**: best structural fit for our harness. `scan_replay()` is designed for exactly
our use case. The Together API key requirement is operationally manageable (we provide our
own key, same as for OpenRouter). The scanner taxonomy is coarse but mappable.

#### AgentDoG (AI45Lab, Shanghai AI Lab)

- **Input**: `trajectory_sample.json` shows a JSON with `profile`, `contents` (list of
  turns: role=user/agent/environment, tool calls as JSON-in-string). Different structure
  but mappable.
- **Output**: Fine-grained diagnosis across three taxonomy dimensions (Risk Source, Failure
  Mode, Real-world Harm). The Unified AgentDoG 1.5 (4B) provides a single classification.
- **Taxonomy**: ✅ Three-dimensional: Risk Source, Failure Mode, Real-world Harm (the third
  dimension is also called "Risk Consequence" in the model configs). Exact category counts
  are **unverified** — sources differ (7/12/6 vs 8/14/10); confirm from the model card
  before writing the output parser.
- **Containerizability**: ❌ Requires serving a 4B–8B model (Qwen3.5-4B or Llama3.1-8B)
  via OpenAI-compatible endpoint. GPU inference required.
- **Adapter effort**: high. Model serving infrastructure + different input serialization
  (agent thoughts, environment actions) + 3D output mapping.

**Assessment**: conceptually the closest to `aidr` (trained detector, fine-grained
classification), but the GPU requirement makes it impractical for a quick second-vendor
test. The taxonomy is the most complete — could be a third vendor test.

#### Lasso Security (`lasso-security/mcp-gateway`)

- **Input**: MCP server traffic only. Not a general transcript analysis tool.
- **Output**: N/A. The gateway passes traffic through with optional basic sanitization.
  The "Security Scanner" analyzes server reputation (URLs, source code) before loading,
  not agent behavior.
- **Taxonomy**: None.
- **Containerizability**: ✅ `pip install mcp-gateway`.
- **Adapter effort**: not applicable — it is not a transcript detector.

**Assessment**: not suitable. It is a gateway tool, not a detector of agentic behavior.

### Updated recommendation (after Fase 1 run)

**LlamaFirewall is the strongest candidate for a second-vendor test.** The existing stock
recommendation below (Invariant Labs) was written before the Fase 1 run, when the harness
design was still being validated. Now that we have a working harness that expects a
structured verdict (label, confidence, technique), LlamaFirewall's `scan_replay()` +
`ScanResult` is the closest match to `aidr`'s interface.

The Together API key requirement for the multi-turn AlignmentCheck scanner is a real
limitation, but it mirrors the existing OpenRouter dependency: we already supply an API
key for the detector — we can supply one for the detector's LLM-as-judge calls too.
The scanner taxonomy is coarse (3 types vs. 14 techniques), but sufficient for the
critical question: does LlamaFirewall also "condemn intent, not effect"? If yes, the
pattern is general. If no, the method has distinguished two detectors — which is the goal.

**Sequencing for a second-vendor test**:
1. Build adapter for LlamaFirewall (1-2 days)
2. Run 31 cases through it (no GPU needed, just API key for AlignmentCheck)
3. Compare intent-vs-effect metrics
4. Decide: if the pattern holds, AgentDoG becomes a third test; if the pattern breaks,
   the method has found a real distinction between detectors

## Expanded search (2026-08-26) — beyond the original keyword

After the Fase 1 run, the search was expanded with a different methodology. The original
search used the rigid keyword "agentic threat detection" and primary sources only. The
expanded search used:

1. **GitHub topic pages** (`ai-guardrails`, `llm-guardrails`, `agent-security`)
2. **Hugging Face** models for trajectory-level safety classification
3. **arXiv papers** with code (Q1-Q3 2026)
4. **Market maps from third parties** (Ansa, PipeLab, Black Hat 2026 analyst reports, VC
   landscape posts) — explicitly excluded by the original search but valuable for discovery

### New candidates discovered

| Candidate | Source | Type | Notes |
|---|---|---|---|
| `cisco-ai-defense/mcp-scanner` | GitHub | MCP scanner | Cisco's own MCP tool scanner |
| `thisisfixer/mcp-scan` | GitHub | MCP scanner | Static+dynamic tool description checks |
| `snyk/agent-scan` | GitHub | Agent scanner | Snyk's runtime agent analyzer (post-Invariant acquisition) |
| `msoedov/agentic_security` | GitHub | Red-team framework | NOT a detector — generates attacks, not verdicts |
| `XSafeAI/XSafeClaw` | GitHub | Interception framework | Hook at framework level, sends trajectory to guard models |
| `dl-eigenart/agentshield-platform` | GitHub | Detection pipeline | 6-layer pipeline (MiniLM + policy engine), <4ms latency |
| `MaxwellCalkin/sentinel-ai` | GitHub | MCP proxy | Real-time guardrail with MCP proxy + Claude Code hooks |
| `CHATS-lab/coding-agent-safety-monitor` | GitHub | Coding-agent monitor | Blocks destructive actions before execution |
| `xiongyuaay/JANUS` (+ Vanguard) | arXiv + GitHub | Trajectory foresight | Predicts future risks from partial trajectory prefixes |
| `AdvRahul/Agentic-Safety` | Hugging Face | Dataset | Training dataset for agent safety classifiers |
| AgentDoG 1.5 (already known, re-evaluated) | Hugging Face | Trajectory classifier | 2B-8B models, 3D taxonomy, OpenAI-compatible API |

### Pre-filtering

Most new candidates are NOT detectors that fit our harness. The pre-filter:

- **MCP scanners** (cisco, fixer, snyk): scan MCP server configurations, not agent
  transcripts. Useful for MCP security but not for our harness.
- **Red-team frameworks** (msoedov/agentic_security): generate attacks, don't classify.
- **MCP proxies** (sentinel-ai): interception layer, not a detector.
- **Coding-agent monitors** (CHATS-lab): too vertical.
- **Dataset** (AdvRahul/Agentic-Safety): useful for training, not for evaluation.

### Candidates worth verifying

| Candidate | Why promising | What to verify |
|---|---|---|
| **AgentDoG 1.5 Unified** (HF) | 2B-8B models, 3D taxonomy, OpenAI-compatible API possible | Can it be served via OpenRouter or lightweight container? |
| **dl-eigenart/agentshield-platform** | 6-layer pipeline, <4ms latency, structured detector | Input/output format? Verdict shape? |
| **snyk/agent-scan** | Snyk's post-Invariant product, could be mature | Detector or scanner? What does it return? |
| **xiongyuaay/JANUS** | arXiv paper with code, trajectory foresight | Is the code runnable? Input format? |

### Updated assessment: AgentDoG 1.5 is back on the table

AgentDoG was previously dismissed as "GPU required" (4B-8B parameters). The expanded
search reveals important details:

- **AgentDoG 1.5 Unified** (4B parameters) provides a single classification score —
  directly mappable to our malicious/benign verdict.
- **Fine-grained models** (FG-Qwen3.5-2B, FG-Llama3.1-8B) output a structured 3D
  diagnosis: Risk Source, Failure Mode, Real-world Harm — a taxonomy system that
  matches our per-technique metric.
- The "Online Agentic Guardrail" component is tied to OpenClaw, but the **models
  themselves** are served via an OpenAI-compatible API (see `trajectory_sample.json`
  and the evaluator code in `guardrail/evaluator.py`).
- If the model can be served via OpenRouter (or a `vllm` container), it becomes the
  strongest candidate: it has the most complete taxonomy of any open-source detector.

A focused verification will determine if AgentDoG 1.5 can be integrated without GPU
infrastructure. See the next section.

## Verification of top candidates (2026-08-26)

Read-only verification of the four candidates flagged as "worth verifying" from the
expanded search. Source: GitHub READMEs, Hugging Face model cards, arXiv papers.

### AgentDoG 1.5 — the strongest candidate, but still GPU-gated

- **HF model**: `AI45Research/AgentDoG1.5-Unified-Qwen3.5-4B` (4B params), plus
  `FG-Qwen3.5-2B/4B/8B` and `FG-Llama3.1-8B` for fine-grained diagnosis.
- **Serving**: requires `vLLM` or `SGLang` — the model card explicitly documents
  `vllm serve AI45Research/AgentDoG1.5-Qwen3.5-4B` and `sglang.launch_server`.
  It is **not** available as a pre-built API endpoint on OpenRouter or Together.
- **API**: the model card mentions "OpenAI-compatible" and "vLLM" — once served, it
  exposes an OpenAI-compatible endpoint, which our harness can call.
- **Input**: structured trajectory JSON (user/agent/environment turns). Our
  transcript format can be mapped.
- **Output**: Unified model produces a single classification score; FG models
  produce a 3D diagnosis (Risk Source, Failure Mode, Real-world Harm).
- **GPU requirement**: confirmed. A 4B-8B model needs GPU inference (4GB+ VRAM
  for 4B, 8GB+ for 8B). A `vllm` container on a machine with a GPU would work.
- **Verdict**: best candidate for a third vendor test **after** LlamaFirewall, if
  GPU infrastructure is available. The 3D taxonomy is the most complete of any
  open-source detector.

### dl-eigenart/agentshield-platform — single-turn classifier, not a trajectory detector

- **What it is**: a prompt-injection/jailbreak/data-exfiltration classifier for
  single-turn text inputs. `shield.classify("text")` returns a verdict with
  `is_injection`, `category`, `confidence`.
- **API**: managed service at `api.agentshield.pro/v1/classify`. Free tier: 100
  req/day. Self-hosted container is on the roadmap (Q2 2026, not yet shipped).
- **Input**: single text string, not a transcript. Multi-turn session defense is
  on the roadmap ("Q2 2026" — not yet shipped).
- **Taxonomy**: injection categories (prompt_injection, jailbreak, data_exfiltration,
  none). Coarser than our 14-technique dataset.
- **Verdict**: not suitable. It is a prompt-level classifier, not a trajectory-level
  detector. The self-hosted container is not yet available.

### snyk/agent-scan — MCP server scanner, not a transcript detector

- **What it is**: CLI tool that discovers MCP servers, agent skills, and scans them
  for prompt injections, vulnerabilities, and malware payloads. Works by starting
  MCP servers and inspecting their tool descriptions.
- **Input**: MCP configuration files (JSON), not agent transcripts.
- **Output**: risk scores per MCP server/skill, with vulnerability categories (not
  a malicious/benign verdict on a transcript).
- **License**: source available on GitHub, but usage requires a Snyk API token.
- **Verdict**: not suitable. It is a static/dynamic scanner for MCP infrastructure,
  not a trajectory-level detector. Related to Invariant (same parent company Snyk)
  but different product.

### xiongyuaay/JANUS (+ Vanguard) — research code, not a production detector

- **What it is**: a research framework for training predictive guardrails that
  anticipate future risks from partial trajectories. Paper + code (July 2026).
- **Model**: Vanguard (Hugging Face: `yuaay/vanguard`), trained via CoAA-RL.
- **Input**: partial trajectory prefix (list of turns).
- **Output**: two-stage prediction: (1) anticipated future summary, (2) safety
  adjudication (block/allow).
- **Readiness**: research code, not a production-grade detector. The repo has a
  single contributor, no releases, no documentation for integration.
- **Verdict**: not suitable for a quick second-vendor test. The research is
  interesting and worth following, but the code is not ready for integration.

### Updated recommendation (expanded search)

| Candidate | Suitability | Barrier | Next step |
|---|---|---|---|
| **LlamaFirewall** | ✅ Best fit | Together API key for AlignmentCheck | Build adapter (1-2 days) |
| **AgentDoG 1.5** | ⚠️ Strong if GPU is available | GPU + vLLM/SGLang serving | Try via OpenRouter if available |
| **AgentShield** | ❌ Single-turn only | No trajectory support | Revisit when multi-turn is released |
| **Snyk Agent Scan** | ❌ MCP scanner | Not a transcript detector | Not applicable |
| **JANUS/Vanguard** | ❌ Research code | Not production-ready | Follow for future maturity |

**Conclusion**: the expanded search found no new candidate that is both (a) a genuine
multi-turn trajectory detector and (b) immediately reachable without GPU or contact-sales.
LlamaFirewall remains the strongest candidate for a second-vendor test. AgentDoG 1.5 is
worth verifying on OpenRouter (if the model is available there) as a fallback.

## External research update (2026-08-26) — lightweight models found

A parallel research pass by an external colleague confirmed the same vendor landscape but
found two important updates that change the feasibility assessment.

### AgentDoG 1.5 lightweight models (0.8B, 2B)

> **CORRECTED 2026-08-26 — verificato direttamente su Hugging Face** (API catalogo
> modelli + `config.json` reali, non da fonti secondarie). Le varianti 0.8B di AgentDoG 1.5
> sono **due** (Base e FG), non tre. **"Unified" esiste solo a 4B**
> (`AgentDoG1.5-Unified-Qwen3.5-4B`). Inoltre l'architettura è **generativa**
> (`Qwen3_5ForConditionalGeneration`, senza `id2label`/`label2id`/`num_labels`): il
> `pipeline_tag: text-classification` è solo metadata HF — il modello NON è un
> classificatore con testa dedicata e NON va caricato con `pipeline("text-classification")`.

AgentDoG 1.5 released smaller variants that were not previously evaluated. Per il taglio
0.8B esistono **due** varianti:

- **AgentDoG1.5-Qwen3.5-0.8B** (Base/coarse-grained): sola moderazione binaria — emette
  `safe` oppure `unsafe`.
- **AgentDoG1.5-FG-Qwen3.5-0.8B** (fine-grained): diagnosi della sola traiettoria non
  sicura — emette la tassonomia 3D.

La variante **Unified** esiste solo a **4B** (`AgentDoG1.5-Unified-Qwen3.5-4B`): binario +
3D in un unico flusso, ma richiede GPU.

Architettura (verificata da `config.json`, 2026-08-26): `Qwen3_5ForConditionalGeneration`,
`vocab_size=248320`, nessuna testa di classificazione. È un LLM generativo: l'output va
estratto con regex, e lo score (se serve) va calcolato dai logit dei token `safe`/`unsafe`,
non da una pipeline di classificazione.

Key implications for our harness:
- **0.8B runs on CPU** via standard transformers. A container with `pip install transformers`
  is sufficient. No GPU, no vLLM, no SGLang.
- **Input**: serialized multi-turn trajectory (JSON turns formatted as text following the
  model's chat template). Our transcript format is mappable.
- **Output**: testo generativo — `safe`, oppure `unsafe` (+ tassonomia 3D solo col modello
  FG, in una chiamata separata). Da estrarre con regex, non da parsare come JSON puro.
- **Adapter effort**: medium. Serialize transcript → generate → regex-parse. Il modello
  Base basta per la metrica primary (l'unica che pubblichiamo); la 3D richiede il passaggio
  FG separato.

**Assessment**: the 0.8B Base model changes AgentDoG from "GPU required" to "CPU-compatible"
for the label-only metric. The 3D diagnosis (FG) is also CPU-only, but as a separate pass —
an optional descriptive add-on, not part of the measurement.

### LlamaFirewall on OpenRouter — confirmed feasible

Further verification of the AlignmentCheck code confirms:

- `custom_check_scanner.py` passes `api_base_url` and `api_key_env_var` to `LLMClient`.
  The default is Together, but these are constructor parameters, not hardcoded.
- `AlignmentCheckScanner.__init__()` does NOT expose these parameters — it calls
  `super().__init__()` without them. This means a 3-line subclass wrapper is needed:
  ```python
  class OpenRouterAlignmentCheck(AlignmentCheckScanner):
      def __init__(self):
          super().__init__()
          self.llm = LLMClient(
              model_name="meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
              api_base_url="https://openrouter.ai/api/v1",
              api_key_env_var="OPENROUTER_API_KEY",
          )
  ```
- OpenRouter hosts `meta-llama/llama-4-maverick:free` (zero cost for testing). The
  model is compatible with LlamaFirewall's default prompt format.
- OpenRouter requires `HTTP-Referer` and `X-Title` headers. The `LLMClient` uses the
  OpenAI SDK, which accepts `extra_headers` in the client constructor. This requires
  a small patch to `LLMClient` to pass `default_headers`.

**Assessment**: confirmed feasible with a small adapter wrapper. The `:free` mode on
OpenRouter makes testing cost-zero.

### Updated recommendation (after external research)

**Two viable paths, both immediately actionable:**

| Path | What | Cost | Effort | Risk |
|---|---|---|---|---|
| **A — LlamaFirewall on OpenRouter** | Subclass wrapper + `:free` model | $0 | 1 day | AlignmentCheck is experimental |
| **B — AgentDoG 1.5 0.8B local** | Docker container with transformers | $0 | 1-2 days | 0.8B model may be less accurate |

Both paths can be built in parallel. The adapter for Path A uses the same pattern as
`aidr`'s adapter (run container + stdin/stdout JSON). The adapter for Path B uses the
Hugging Face `transformers` library in a lightweight container.

**Recommendation**: start with Path A (LlamaFirewall on OpenRouter) because it requires
no local model download and uses the same API-key pattern as the existing harness. Path B
(AgentDoG 1.5 0.8B) is a fallback if the query-based AlignmentCheck is too slow or if
we need the 3D taxonomy.

Applying the three stated criteria — (a) architectural distance from `aidr`'s own design
(open-source, self-hostable, three separate stages: Sifter/Inspector/Gauntlet), (b) reachability by a
single independent operator without an enterprise budget, and (c) real-world adoption that makes the
audit publicly valuable — **no single candidate wins clean on all three**, and forcing one would repeat
exactly the kind of overconfident, unqualified conclusion this project's own `SPIRIT.md` (principle 3)
exists to avoid.

The market splits cleanly into two groups that trade off (b) against everything else:

- **Nine of the fourteen in-focus candidates are contact-sales-only enterprise SaaS** with no public
  trial technical detail verifiable from a primary source (Lakera, CalypsoAI, Straiker, Obsidian,
  HiddenLayer, Zenity, Prompt Security, Protect AI/Prisma AIRS, Cisco AI Defense, Galileo — that's
  actually ten). Several of these have real, checkable enterprise adoption (Obsidian's $85M Series D
  and T-Mobile/Databricks/Snowflake customers; Straiker's $64M Series A and Amex GBT/Coupa customers;
  Zenity's Gartner recognition) that would make an audit genuinely newsworthy — but none of them are
  reachable by an independent auditor without either a sales conversation or a paid contract, which
  directly conflicts with this project's principle 5 (paid by whoever evaluates a purchase, never by
  the vendor) in the most basic sense: there is no way to even *acquire test access* without becoming
  a prospect in the vendor's own sales pipeline.

- **Four candidates are fully open-source and self-hostable with no paywall at any tier**: Invariant
  Labs (Guardrails + MCP-Scan), Lasso Security's gateway (the SaaS platform on top is closed, but the
  gateway itself is the actual detection surface), LlamaFirewall, and AgentDoG. These are the only
  four where a single operator could actually run the exact same audit methodology this project
  already built for `aidr` — pull the code, run it against the toy agent's real transcripts, verify
  the output — without asking anyone's permission first.

Within that second, actually-reachable group:

- **AgentDoG is the weakest choice on criterion (a)**: it is *the same audit* this project just did —
  open-source detector, self-graded on its own benchmark, same conflict-of-interest shape as `aidr`.
  Auditing it would prove the methodology generalizes (a legitimate reason to pick it eventually) but
  would not stretch the project into new territory the way a structurally different product would.

- **LlamaFirewall scores highest on (c)** by a wide margin — it ships inside `meta-llama/PurpleLlama`,
  a 4,358-star, actively-maintained-as-of-yesterday repository backed by Meta, which makes an audit of
  it unambiguously newsworthy and hard to dismiss as "testing an obscure project nobody uses." It is
  architecturally more different from `aidr` than AgentDoG (a trained BERT classifier for single-turn
  plus a distinct LLM-as-judge chain-of-thought auditor for multi-step alignment, rather than `aidr`'s
  three-stage Sifter/Inspector/Gauntlet pipeline design), though both ultimately combine "a fast
  classifier" with "an LLM judge," so the architectural distance is real but not total. Running
  `AlignmentCheck`/`scan_replay()` at scale requires paying for LLM-judge inference calls (an
  operational cost, not a vendor paywall — the auditor supplies their own API key) which is a real but
  modest barrier compared to contact-sales gating.

- **Invariant Labs scores highest on (a)**: its policy/rule engine (Guardrails) is a genuinely
  different detection paradigm from `aidr`'s pipeline — declarative trace-analysis rules and static
  MCP-server scanning (MCP-Scan) rather than a trained-classifier cascade — so auditing it would test
  a different failure mode entirely (does a human-written policy language actually catch the attacks
  its author didn't think to write a rule for, versus does a trained classifier generalize past its
  training distribution). It also has the single strongest adoption signal among the open, self-hostable
  group (MCP-Scan alone: 2,931 stars, pushed the same day as this research) and a credible acquirer
  (Snyk, an established, publicly-recognized security company) backing continued maintenance — a
  stronger (c) signal than AgentDoG's academic-lab backing, if a weaker one than LlamaFirewall's Meta
  backing.

> **Riverificato 2026-08-27** (vedi `docs/research/2026-08-27-agentdog-verification.md`): questa
> classifica non è superata da un dettaglio successivo (AgentDoG 1.5) — la sezione appena sopra
> ("External research update", riga 561) è già scritta con piena conoscenza di AgentDoG 1.5 0.8B, e la
> riverifica del 27 agosto la conferma e la rafforza con dati freschi (adozione GitHub/HF, citazioni,
> nessuna valutazione indipendente). Nota anche: `invariantlabs-ai/mcp-scan` è stato rinominato/trasferito
> a `snyk/agent-scan` in seguito all'acquisizione (stesso repository ID, storia/stelle preservate), ora
> con attività più recente di quanto risultasse qui.

**Net recommendation, stated as a genuine tradeoff rather than a forced winner: Invariant Labs
(Guardrails + MCP-Scan) is the strongest overall next candidate** — it is the only one of the four
reachable options that is both architecturally distinct from `aidr` *and* carries real, verifiable
adoption (2,931 stars, active same-day commits, a named security-industry acquirer), at the cost of
requiring the auditor to actually write Invariant policies by hand before there is anything to
score — the tool ships as a policy language, not a pre-trained model, so "does it catch technique
T00xx" first requires deciding what policy *should* catch it, which is a different and arguably harder
audit design problem than scoring a black-box classifier's verdict the way this project already does
for `aidr`. **LlamaFirewall is the strongest fallback** if that policy-authoring step turns out to be
too large a redesign of the existing measurement pipeline — it slots into roughly the same
black-box-verdict-scoring shape as `aidr` already does, at the cost of being architecturally the least
different of the two, and of needing the auditor to provision LLM-judge API access for the multi-step
`AlignmentCheck` component to even run.

## Sources consulted

- GitHub REST API (`gh api` via WebFetch on `api.github.com/repos/<owner>/<repo>`) for all
  stars/license/push-date metadata cited: `lasso-security/mcp-gateway`, `invariantlabs-ai/invariant`,
  `invariantlabs-ai/mcp-scan`, `protectai/llm-guard`, `akasecurity/ai-tc`,
  `FareedKhan-dev/agentic-threat-detection`.
- Official vendor sites/docs fetched directly: `docs.lakera.ai/docs/agent-security`,
  `docs.lakera.ai/docs/defenses`, `calypsoai.com/inference-platform/` (TLS error, noted),
  `calypsoai.com/insights/an-introduction-to-agentic-ai/` (TLS error, noted),
  `straiker.ai/`, `straiker.ai/blog/top-agentic-ai-security-platforms`,
  `obsidiansecurity.com/academy/mcp-tool-call-monitoring`, `obsidiansecurity.com/`,
  `lasso.security/use-cases/mcp`, `lasso.security/`,
  `github.com/invariantlabs-ai/invariant`, `github.com/meta-llama/PurpleLlama/tree/main/LlamaFirewall`,
  `github.com/NVIDIA/NeMo-Guardrails`, `github.com/guardrails-ai/guardrails`,
  `galileo.ai/`, `v2docs.galileo.ai/concepts/metrics/safety-and-compliance/prompt-injection`,
  `hiddenlayer.com/news/hiddenlayer-unveils-new-agentic-runtime-security-capabilities-for-securing-autonomous-ai-execution`, `hiddenlayer.com/`,
  `zenity.io/platform/ai-security-platform/aidr`, `zenity.io/`,
  `prompt.security/`, `prompt.security/solutions/agentic-ai-security-and-governance`,
  `protectai.com/` (redirect target followed), `paloaltonetworks.com/ai-security/prisma-airs`,
  `kovrr.com/blog-post/monitoring-ai-agent-behavior-in-production`.
- Official acquirer press releases/blogs fetched directly: `f5.com/company/blog/outcome-analysis`,
  `sentinelone.com/blog/a-new-chapter-for-ai-and-cybersecurity-sentinelone-acquires-prompt-security/`,
  `blogs.cisco.com/ai/security-for-the-agentic-era-cisco-ai-defense-breaks-new-ground`,
  `blogs.cisco.com/news/cisco-announces-the-intent-to-acquire-galileo` (via search-result summary),
  `snyk.io/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation/` (via
  search-result summary).
- Pages that returned an error and were flagged rather than silently substituted with a secondary
  source: `calypsoai.com` (expired TLS certificate, both product pages), `cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-ds.html` (HTTP 403), `cisco.com/site/us/en/products/security/ai-defense/ai-runtime/index.html` (HTTP 403), `prompt.security/products/mcp-server-security` (HTTP 404, correct URL not found within this pass).
- Reused without re-verification, itself already primary-source-checked one day earlier: AgentDoG card
  and the `meta-llama/PurpleLlama` parent-repo star/date figures, both from
  `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`.
- `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md` and `catalog/vendor_taxonomy_snapshot.yaml`
  consulted for the exact T0001-T0014 taxonomy this file's taxonomy comparisons are made against.
