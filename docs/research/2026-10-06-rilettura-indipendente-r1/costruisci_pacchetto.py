"""Costruisce i pacchetti della rilettura indipendente R1 (protocollo: README.md qui accanto).

Uso: python costruisci_pacchetto.py <cartella di uscita, fuori dal repo>
     python costruisci_pacchetto.py --controllo <stessa cartella>

Il primo comando crea <uscita>/fase-1 e <uscita>/fase-2 e CANCELLA la cartella se esiste,
comprese le consegne di R1: dopo la fase 1 non va rilanciato. Il secondo crea solo
<uscita>/controllo, per il controllo delle regole corrette. La mappa dei run rinominati si scrive qui accanto
(mappa-run.json), fuori dai pacchetti. Le copie dei documenti si fanno per sezioni, senza
riscrivere il testo; le sole righe cambiate sono elencate in SOSTITUZIONI.
"""
import csv
import json
import random
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DESIGN = REPO / "docs/design"
REPORTS = REPO / "docs/reports"
SEED = 20261006
RUNS = [
    "agentic-threat-detection-2026-08-19",
    "aidr-2026-08-26",
    "atlas-6gap-aidr-2026-09-01",
    "llamafirewall-2026-08-28",
    "llamafirewall-combined-2026-09-04",
]
CODE = ["agent_loop.py", "tools.py", "state.py", "criteria.py", "schema.py"]

INTESTAZIONE_ALBERO = (
    "# Albero di decisione v2: fasi 0 e 1\n\n"
    "Copia per sezioni di `2026-10-02-albero-v2.md` per la fase 1 della rilettura indipendente. "
    "Il testo delle sezioni è invariato, salvo le righe indicate come sostituite.\n\n"
)
# (vecchio, nuovo): uniche modifiche ammesse al testo copiato
SOSTITUZIONI = [
    ("| `ticket_false_prior_authorization_claim`, `bulk_export_to_partner_address`, "
     "`piecemeal_lookup_avoids_bulk_export`, `atlas_t0012_valid_accounts_impersonation_update_account` |",
     "| da classificare (vedi sotto) |"),
    ("| `card_digits_smuggled_as_reference_number`, `cross_customer_lookup_for_unrelated_comparison`, "
     "`diagnostic_command_probes_external_url`, `repeated_status_checks_without_cause`, "
     "`email_redirected_to_unverified_new_address`, `atlas_t0077_html_payload`, "
     "`atlas_t0077_markdown_link_payload`, `atlas_t0103_t0108_subagent_attempt`, "
     "`atlas_t0006_t0084_system_prompt_extraction`, `atlas_t0006_t0084_tool_surface_enum`, "
     "`atlas_t0012_valid_accounts_vip_ticket_abuse` |",
     "| da classificare: i 15 casi malevoli con vettore richiesta che non sono R1 né R2 si "
     "classificano in R3 o R4 con il criterio qui sotto |"),
    ("è scattata in 6 sessioni su\n  138, nessuna segnalata.", "è scattata in 6 sessioni su\n  138."),
]


def sezioni(testo):
    """Divide un documento markdown in sezioni di livello 2: {titolo: testo}."""
    parti = re.split(r"(?m)^(?=## )", testo)
    return {p.splitlines()[0]: p for p in parti}


def albero_fase_0_1():
    s = sezioni((DESIGN / "2026-10-02-albero-v2.md").read_text(encoding="utf-8"))
    giudizi = s["## I giudizi"].split("### Elenco motivato dei casi ⚑")[0]
    giudizi += "Per ogni giudizio dubbio, scrivi la tua decisione e il motivo.\n\n"
    testo = (INTESTAZIONE_ALBERO + s["## Cosa si misura"] + s["## Fase 0: il caso (una volta per ognuno dei 38 casi)"]
             + s["## Fase 1: cosa è successo nella sessione (una volta per sessione)"] + giudizi
             + s["## Limiti dichiarati una volta per tutto il dataset"])
    for vecchio, nuovo in SOSTITUZIONI:
        assert testo.count(vecchio) == 1, f"testo da sostituire non trovato: {vecchio[:60]}"
        testo = testo.replace(vecchio, nuovo)
    return testo


def albero_fase_2():
    s = sezioni((DESIGN / "2026-10-02-albero-v2.md").read_text(encoding="utf-8"))
    return ("# Albero di decisione v2: fase 2\n\nCopia per sezioni di `2026-10-02-albero-v2.md`.\n\n"
            + s["## Fase 2: come si giudica ogni detector"] + s["## Esempio percorso per intero"])


def sistema_parte_a():
    s = sezioni((DESIGN / "2026-10-01-sistema-di-riferimento.md").read_text(encoding="utf-8"))
    return ("# Sistema di riferimento: elementi che un sistema reale avrebbe\n\n"
            "Copia della parte A di `2026-10-01-sistema-di-riferimento.md`.\n\n"
            + s["## Parte A: elementi che un sistema reale avrebbe (per ⚑2)"])


CODE_DETECTOR = ["aidr/adapter.py", "aidr/evaluate_case.py", "llamafirewall/adapter.py",
                 "llamafirewall/evaluate_case.py", "llamafirewall/evaluate_case_combined.py"]


def controllo(out):
    """Controllo delle regole corrette (README, "Controllo delle regole corrette").

    Crea solo <out>/controllo, accanto a fase-1 e fase-2, che contengono le consegne di R1 e
    non si toccano. Usa la stessa mappa dei run (mappa-run.json, già applicata ai transcript
    di fase-1) e le sessioni di controllo-sessioni.csv.
    """
    assert REPO not in out.parents, "il pacchetto va fuori dal repo"
    assert (out / "fase-1" / "transcripts").is_dir(), "manca fase-1: il controllo usa i suoi transcript"
    c = out / "controllo"
    if c.exists():
        shutil.rmtree(c)
    righe = list(csv.DictReader((HERE / "controllo-sessioni.csv").open(encoding="utf-8")))
    (c / "code").mkdir(parents=True)
    for nome in CODE:
        shutil.copy(REPO / "src/toy_agent" / nome, c / "code" / nome)
    for nome in CODE_DETECTOR:
        dest = c / "code-detector" / nome
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "src/detector_adapter/vendors" / nome, dest)
    shutil.copytree(REPO / "dataset", c / "dataset")
    shutil.copytree(out / "fase-2" / "verdetti", c / "verdetti")
    for r in righe:
        src = out / "fase-1" / "transcripts" / r["run_pacchetto"] / f"{r['case_id']}.transcript.json"
        dest = c / "transcripts" / r["run_pacchetto"] / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
    with (c / "sessioni.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["run", "case_id", "regole"])
        for r in righe:
            w.writerow([r["run_pacchetto"], r["case_id"], r["regole"]])
    shutil.copy(DESIGN / "2026-10-02-albero-v2.md", c / "albero-v2.md")
    (c / "sistema-di-riferimento.md").write_text(sistema_parte_a(), encoding="utf-8", newline="\n")
    for doc in ["2026-09-30-tabella-ambiti-detector.md", "2026-10-07-proposta-ambito-per-domanda.md"]:
        shutil.copy(DESIGN / doc, c / doc)
    shutil.copy(HERE / "CONTROLLO-ISTRUZIONI.md", c / "ISTRUZIONI.md")
    n = sum(1 for _ in (c / "transcripts").rglob("*.transcript.json"))
    print(f"controllo: {n} transcript su {len(righe)} sessioni")


def main():
    if sys.argv[1] == "--controllo":
        controllo(Path(sys.argv[2]).resolve())
        return
    out = Path(sys.argv[1]).resolve()
    assert REPO not in out.parents, "il pacchetto va fuori dal repo"
    if out.exists():
        shutil.rmtree(out)
    nomi = [f"run_{c}" for c in "ABCDE"]
    ordine = RUNS[:]
    random.Random(SEED).shuffle(ordine)
    mappa = dict(zip(nomi, ordine))
    (HERE / "mappa-run.json").write_text(json.dumps(mappa, indent=1), encoding="utf-8", newline="\n")

    f1 = out / "fase-1"
    (f1 / "code").mkdir(parents=True)
    for nome in CODE:
        shutil.copy(REPO / "src/toy_agent" / nome, f1 / "code" / nome)
    shutil.copytree(REPO / "dataset", f1 / "dataset")
    for nome, run in mappa.items():
        shutil.copytree(REPORTS / run / "raw", f1 / "transcripts" / nome)
    (f1 / "albero-fase-0-1.md").write_text(albero_fase_0_1(), encoding="utf-8", newline="\n")
    (f1 / "sistema-di-riferimento.md").write_text(sistema_parte_a(), encoding="utf-8", newline="\n")
    shutil.copy(HERE / "FASE-1-ISTRUZIONI.md", f1 / "ISTRUZIONI.md")

    f2 = out / "fase-2"
    (f2 / "verdetti").mkdir(parents=True)
    for nome, run in mappa.items():
        shutil.copy(REPORTS / run / "verdicts.jsonl", f2 / "verdetti" / f"{nome}.verdicts.jsonl")
    (f2 / "albero-fase-2.md").write_text(albero_fase_2(), encoding="utf-8", newline="\n")
    for doc in ["2026-09-30-tabella-ambiti-detector.md", "2026-10-02-elenco-casi-flag.md",
                "2026-10-01-registro-modifiche-v2.md"]:
        shutil.copy(DESIGN / doc, f2 / doc)
    shutil.copy(HERE / "FASE-2-ISTRUZIONI.md", f2 / "ISTRUZIONI.md")

    n = sum(1 for _ in (f1 / "transcripts").rglob("*.transcript.json"))
    print(f"fase-1: {n} transcript; mappa: {mappa}")


if __name__ == "__main__":
    main()
