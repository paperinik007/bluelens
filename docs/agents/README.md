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
| `council-skeptic` | Review adversarial del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-risk` | Review rischi del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-pragmatist` | Review YAGNI del design | pi (~/.pi/agent/agents/), Claude Code |
| `council-advocate` | Review usabilità del design | pi (~/.pi/agent/agents/), Claude Code |