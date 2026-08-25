# Agent definitions — canonical, portable

Gli agenti qui definiti sono la versione canonica, portabile tra pi e Claude Code.

## Come adattare un agente da un ambiente all'altro

| Elemento | pi | Claude Code |
|---|---|---|
| `tools` | `read, write, edit, bash, grep, find, ls` | `Read, Write, Edit, Bash, Glob, Grep` |
| `model` | omesso (eredita sessione) o modello OpenRouter | `sonnet`, `haiku`, `opus` |
| Invocazione | `subagent(agent: "nome", agentScope: "both")` | `Agent` tool / `Task` tool |
| Collocazione | `~/.pi/agent/agents/` o `.pi/agents/` | `~/.claude/agents/` |

Il corpo del prompt è identico. Se un agente ha varianti specifiche per ambiente,
sono documentate nel file stesso con sezioni `<!-- pi -->` / `<!-- claude -->`.

## Agenti definiti

| Agente | Ruolo | Ambienti |
|---|---|---|
| `implementer` | Implementa un task con TDD, committa | pi (.pi/agents/), Claude Code |
| `reviewer` | Task review (spec + quality) e final whole-branch review, read-only | pi (.pi/agents/), Claude Code |
| `council-skeptic` | Review adversarial del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-risk` | Review rischi del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-pragmatist` | Review YAGNI del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-advocate` | Review usabilità del design | pi (~/.pi/agent/agents/), Claude Code |

## Flusso SDD (ordine di invocazione)

1. `implementer` — implementa il task (TDD, commit)
2. `reviewer` — task review: spec compliance (✅/❌) + task quality (Approved/Needs fixes); se ❌ → fix loop (re-dispatch implementer + re-review scoped, max 5 round)
3. A fine piano: `reviewer` sul diff `MERGE_BASE..HEAD` — final whole-branch review (Critical/Important/Minor + Ready to merge?)
4. `finishing-a-development-branch` — verify test + menu merge/PR/keep

Nota: il `reviewer` di default di pi (`~/.pi/agent/agents/reviewer.md`) ha `model:
claude-sonnet-4-5` hardcoded — per il nostro flusso serve la variante project-local
senza `model` (eredita la sessione), come `implementer`.