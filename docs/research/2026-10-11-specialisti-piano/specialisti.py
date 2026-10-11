"""Revisione del piano del run v3 da parte di due specialisti di famiglie diverse (2026-10-11)."""
import concurrent.futures as cf
import json
import pathlib
import urllib.request

G = pathlib.Path(r'C:\Users\salva\Documents\github')
A = G / 'agentic-security-audits'
OUT = A / 'docs' / 'research' / '2026-10-11-specialisti-piano'
OUT.mkdir(parents=True, exist_ok=True)
key = [l.split('=', 1)[1].strip().strip('"').strip("'")
       for l in (A / '.env').read_text(encoding='utf-8').splitlines()
       if l.startswith('AGENT_OPENROUTER_API_KEY=')][0]

piano = (A / 'docs/design/2026-10-11-piano-run-v3.md').read_text(encoding='utf-8')
rev = (A / 'docs/design/2026-10-09-revisione-modello.md').read_text(encoding='utf-8')
sfere = (A / 'docs/design/2026-10-11-sfere-giudici.md').read_text(encoding='utf-8')

CONTESTO = """Il progetto misura dei "giudici": prodotti di sicurezza (aidr, PromptGuard 2,
AlignmentCheck) che sorvegliano un agente AI di supporto clienti e dicono se una sessione è
malevola. Il principio della misura è: un caso è un segnale noto immesso nel sistema, il
giudice è lo strumento, anche la lettura di chi misura è uno strumento con un suo errore.

Sotto trovi tre documenti: (1) il piano del run nuovo, da rivedere; (2) il file delle
decisioni sul modello di misura, scritto in ordine di tempo, dove una decisione successiva
può correggere una precedente (vale la più recente, se lo dice); (3) le sfere dichiarate dei
tre giudici. Il modello (documenti 2 e 3) è chiuso: rivedi il piano, e il modello solo dove
il piano ne dipende.
"""

RUOLI = {
    'metodologia': """Sei uno specialista di metodologia della misura: disegno sperimentale,
statistica per conteggi piccoli, accordo tra lettori (inter-rater), regole di arresto,
separazione tra insieme di sviluppo e di verifica, errori sistematici di chi misura.""",
    'sicurezza': """Sei uno specialista di sicurezza degli agenti AI: red teaming di agenti che
usano strumenti, prompt injection diretta e indiretta, tool poisoning, cataloghi degli
attacchi (OWASP Top 10 for Agentic Applications, MITRE ATLAS), realismo degli ambienti di
prova, cosa un sistema di rilevamento può e non può vedere.""",
}

COMPITO = """
Cerca soltanto, nel tuo campo:
A. gap e rischi: cose che il piano non prevede e che possono rendere la misura sbagliata o
   non interpretabile, con il meccanismo concreto;
B. scelte del piano che il tuo campo considera sbagliate o deboli, con l'alternativa completa
   (numeri compresi, se servono);
C. affermazioni presentate come fatti che i documenti non sostengono;
D. al massimo UNO specialista di un altro campo che servirebbe, solo se c'è un buco che né tu
   né l'altro specialista (l'altro è di {altro}) coprite: nomina il campo e il buco preciso.
   Se non serve, scrivi "nessuno".

Non suggerire cambi di stile o di parole. Non riaprire decisioni del modello che i documenti
motivano, a meno che tu non mostri che contraddicono il principio della misura. Se non trovi
niente in una categoria, scrivilo.

Per ogni punto: categoria; i passi esatti coinvolti (citati); perché è un problema; un
esempio concreto (se possibile un caso nominato nei documenti); gravità (alta: cambia cosa si
conta o rende la misura non valida; media: cambia come si legge; bassa: chiarezza). Rispondi
in italiano. Metti per primi i punti di gravità alta.
"""

DOCS = ("\n\n=== DOCUMENTO 1: piano del run ===\n" + piano +
        "\n\n=== DOCUMENTO 2: file delle decisioni sul modello ===\n" + rev +
        "\n\n=== DOCUMENTO 3: sfere dei giudici ===\n" + sfere)

SPEC = {
    'metodologia': ('google/gemini-3.1-pro-preview', 'sicurezza degli agenti AI'),
    'sicurezza': ('deepseek/deepseek-v4-pro-0813', 'metodologia della misura'),
}


def prompt(ruolo):
    return RUOLI[ruolo] + "\n\n" + CONTESTO + COMPITO.format(altro=SPEC[ruolo][1]) + DOCS


def call(ruolo):
    model = SPEC[ruolo][0]
    p = prompt(ruolo)
    (OUT / f'input-{ruolo}.md').write_text(p, encoding='utf-8')
    body = {'model': model, 'temperature': 0, 'messages': [{'role': 'user', 'content': p}]}
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Authorization': f'Bearer {key}',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.loads(r.read().decode('utf-8'))
    (OUT / f'output-{ruolo}.md').write_text(
        f"# Specialista: {ruolo} ({resp.get('model', model)}, fornitore "
        f"{resp.get('provider', '?')})\n\n{resp['choices'][0]['message']['content']}\n",
        encoding='utf-8')
    return ruolo, resp.get('model'), resp.get('provider'), resp.get('usage', {}).get('cost')


if __name__ == '__main__':
    with cf.ThreadPoolExecutor(2) as ex:
        for res in ex.map(call, SPEC):
            print(res)
