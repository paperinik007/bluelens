# Controllo indipendente delle schede v3 — README

**Stato**: prompt preparato il 2026-10-21, lancio in attesa di esecuzione.
**File di prompt**: `2026-10-19-prompt-pi-schede.md`.
**File di output atteso**: `esito-controllo.md` (creato dopo il lancio).

## Cosa c'è qui

- `2026-10-19-prompt-pi-schede.md` — il prompt per il modello di controllo.
- `esito-controllo.md` — da creare dopo il lancio.

## Come lanciare il controllo

Il modello di controllo previsto è `google/gemini-2.0-flash` via OpenRouter. La
directory non contiene uno script di lancio per evitare di legare l'audit a una
specifica API; il proprietario sceglie come invocarlo. Due modi possibili:

### Via script Python (con OpenRouter via `openai`)

```python
import os
import openai
from pathlib import Path

prompt = Path("docs/research/2026-10-19-controllo-schede/2026-10-19-prompt-pi-schede.md").read_text()
cases_dir = Path("dataset_v3/cases/")
case_files = sorted(cases_dir.glob("*.yaml"))
cases_text = "\n\n---\n\n".join(f"# {f.name}\n{f.read_text()}" for f in case_files)

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["AGENT_OPENROUTER_API_KEY"],
)

response = client.chat.completions.create(
    model="google/gemini-2.0-flash",
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Ecco le 18 schede da controllare:\n\n{cases_text}"},
    ],
    temperature=0.0,
)

Path("docs/research/2026-10-19-controllo-schede/esito-controllo.md").write_text(
    response.choices[0].message.content
)
```

### Via altra sessione di un modello compatibile

Se il proprietario non ha `openai` configurato, può incollare il prompt in un'altra
sessione che usa `gpt-5.4-mini` (o un modello equivalente di un'altra famiglia) e
allegare le 15 schede come testo. L'output va incollato in `esito-controllo.md`.

## Cosa fare dopo il lancio

1. `pi` legge `esito-controllo.md`.
2. Per ogni scheda con errori bloccanti, corregge la scheda e riporta la correzione
   nel registro.
3. Per gli errori non bloccanti, li annota per chiuderli nelle iterazioni successive.
4. Se il prompt 2 trova pattern ricorrenti (es. "tutte le `disguised_injection`
   hanno un seed_turn che inizia con 'Hi'"), pi decide se intervenire sul template
   o lasciare così.
