"""Esecuzione esterna dello specialista di metodologia (2026-11-11): stessa definizione, solo testo, nessun accesso al repository."""
import json
import pathlib
import time
import urllib.request

A = pathlib.Path(r'C:\Users\salva\Documents\github\agentic-security-audits')
OUT = A / 'docs' / 'research' / '2026-11-11-specialisti-congelamento' / 'esecuzioni' / 'metodologia-esterna'
OUT.mkdir(parents=True, exist_ok=True)
MODEL = 'deepseek/deepseek-v3.2'
PROVIDER = 'AtlasCloud'

key = [l.split('=', 1)[1].strip().strip('"').strip("'")
       for l in (A / '.env').read_text(encoding='utf-8').splitlines()
       if l.startswith('AGENT_OPENROUTER_API_KEY=')][0]

definizione = (A / 'docs/research/2026-11-11-specialisti-congelamento/agenti/specialista-metodologia.md').read_text(encoding='utf-8')
corpo = definizione.split('---', 2)[2].strip()  # senza intestazione dell'agente

DOCS = [
    'docs/design/2026-10-11-piano-run-v3.md',
    'docs/design/2026-11-05-limiti-dichiarati-run-v3.md',
    'docs/research/2026-11-05-revisore/RELAZIONE.md',
    'docs/research/2026-10-22-prova-generale-agente/README.md',
    'docs/design/2026-10-11-sfere-giudici.md',
    'dataset_v3/controls/README.md',
    'docs/research/2026-11-11-campioni-controllo/ESITO.md',
]

NOTA = ("NOTA SULL'ESECUZIONE: non hai accesso al repository e non hai strumenti. I documenti elencati nella sezione "
        "'Cosa leggere' sono incollati qui sotto per intero, ciascuno con il suo percorso. Dove la definizione chiede "
        "file:riga come PROVA, scrivi il percorso del documento e la sezione, oppure 'solo testo'. Non puoi verificare "
        "sul codice: dichiaralo nei punti che lo richiederebbero.\n")

user = NOTA + ''.join(f"\n\n=== DOCUMENTO: {d} ===\n" + (A / d).read_text(encoding='utf-8') for d in DOCS)
(OUT / 'istruzione-sistema.md').write_text(corpo, encoding='utf-8')
(OUT / 'input-utente.md').write_text(user, encoding='utf-8')

body = {'model': MODEL, 'temperature': 0,
        'provider': {'order': [PROVIDER], 'allow_fallbacks': False},
        'messages': [{'role': 'system', 'content': corpo}, {'role': 'user', 'content': user}]}
t0 = time.time()
req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                             data=json.dumps(body).encode('utf-8'),
                             headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=900) as r:
    resp = json.loads(r.read().decode('utf-8'))
dt = time.time() - t0
(OUT / 'output.md').write_text(
    f"# Specialista metodologia, esecuzione esterna ({resp.get('model')}, fornitore {resp.get('provider')})\n\n"
    f"{resp['choices'][0]['message']['content']}\n", encoding='utf-8')
meta = {'model': resp.get('model'), 'provider': resp.get('provider'), 'usage': resp.get('usage'), 'secondi': round(dt, 1)}
(OUT / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
print(meta)
