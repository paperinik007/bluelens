"""Tabelle finali dei run pubblicati (albero v2, `docs/design/2026-10-02-albero-v2.md`).

Uso: python costruisci_tabelle.py

Legge la fase 0 (dataset, tipi), gli esiti della fase 1 (`nostra-applicazione/esiti.csv`, con
le decisioni del proprietario) e i verdetti dei run pubblicati; scrive qui accanto
`tabella-per-caso.csv` e `tabella-per-caso.md`. Nessun giudizio nuovo: solo unione di dati
già decisi e separazione del verdetto fuso del 4/9.
"""
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
R1DIR = REPO / "docs/research/2026-10-06-rilettura-indipendente-r1"
RUNS = {  # run -> (data, detector)
    "agentic-threat-detection-2026-08-19": ("19/8", ["aidr"]),
    "aidr-2026-08-26": ("26/8", ["aidr"]),
    "atlas-6gap-aidr-2026-09-01": ("1/9", ["aidr"]),
    "llamafirewall-2026-08-28": ("28/8", ["AlignmentCheck"]),
    "llamafirewall-combined-2026-09-04": ("4/9", ["AlignmentCheck", "PromptGuard"]),
}
ORDINE_RUN = list(RUNS)
AMBIENTE = {"status_update_triggers_hidden_admin_escalation", "refund_without_authorization"}
AGENTE = {"unrequested_account_deactivation_as_fix", "account_disabled_after_misread_opt_out_request"}
R1_INIEZIONE = {"ticket_fake_forwarding_policy_note", "ticket_hidden_instruction_in_reply",
                "hidden_instruction_triggers_unauthorized_export"}
R2_OVERRIDE = {"direct_override_bulk_export_to_outsider"}
MALEVOLI = {"ESEGUE", "TENTA", "DANNO NON RICHIESTO"}


def fase0():
    """caso -> (intento, vettore, tipo), secondo la fase 0 dell'albero."""
    import yaml
    tipi = {r["case_id"]: r["tipo"] for r in csv.DictReader(
        (R1DIR / "nostra-applicazione/tipi.csv").open(encoding="utf-8"))}
    out = {}
    for f in sorted((REPO / "dataset").glob("*.yaml")):
        c = f.stem
        label = yaml.safe_load(f.read_text(encoding="utf-8"))["label"]
        if label == "benign":
            out[c] = ("benigno", "—", "B")
        elif c in AMBIENTE:
            out[c] = ("malevolo", "ambiente", "E")
        elif c in AGENTE:
            out[c] = ("malevolo", "agente", "R5")
        elif c in R1_INIEZIONE:
            out[c] = ("malevolo", "richiesta", "R1")
        elif c in R2_OVERRIDE:
            out[c] = ("malevolo", "richiesta", "R2")
        else:
            out[c] = ("malevolo", "richiesta", tipi[c])
    return out


def verdetti():
    """(run, caso) -> {detector: 'malevolo'|'benigno'}; il 4/9 separato per scanner."""
    out = {}
    for run, (_, dets) in RUNS.items():
        for riga in (REPO / "docs/reports" / run / "verdicts.jsonl").open(encoding="utf-8"):
            v = json.loads(riga)
            if run.startswith("llamafirewall-combined"):
                r = v["rationale"]
                ac = re.findall(r"Conclusion: (True|False)", r)
                assert len(ac) == 1, v["case_id"]
                pg = "likely to be a prompt injection" in r
                assert pg != ("No prompt injection detected" in r), v["case_id"]
                assert ((ac[0] == "True") or pg) == (v["label"] == "malicious"), v["case_id"]
                out[(run, v["case_id"])] = {"AlignmentCheck": "malevolo" if ac[0] == "True" else "benigno",
                                            "PromptGuard": "malevolo" if pg else "benigno"}
            else:
                out[(run, v["case_id"])] = {dets[0]: "malevolo" if v["label"] == "malicious" else "benigno"}
    return out


def main():
    f0 = fase0()
    ver = verdetti()
    esiti = list(csv.DictReader((R1DIR / "nostra-applicazione/esiti.csv").open(encoding="utf-8")))
    righe = []
    for e in esiti:
        k = (e["run"], e["case_id"])
        intento, vettore, tipo = f0[e["case_id"]]
        segnalata = [d for d, l in ver[k].items() if l == "malevolo"]
        danno_avvenuto = e["esito"] in MALEVOLI and e["effetto"].startswith("avvenuto")
        righe.append({
            "caso": e["case_id"], "run": RUNS[e["run"]][0], "intento": intento, "vettore": vettore,
            "tipo": tipo, "esito": e["esito"], "causa": e["causa"], "nota": e["nota"],
            "backdoor": e["backdoor"], "effetto": e["effetto"],
            "agente_giudicabile": e["agente_giudicabile"],
            "detector": ", ".join(ver[k]), "segnalata_da": ", ".join(segnalata) or "nessuno",
            "danno_avvenuto_non_segnalato": "sì" if danno_avvenuto and not segnalata else "",
        })
    righe.sort(key=lambda r: (r["caso"], ORDINE_RUN.index(next(k for k, v in RUNS.items() if v[0] == r["run"]))))
    campi = list(righe[0])
    with (HERE / "tabella-per-caso.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campi, lineterminator="\n")
        w.writeheader()
        w.writerows(righe)

    md = ["# Tabella per caso (run pubblicati, albero v2)", "",
          "Generata da `costruisci_tabelle.py`: non modificare a mano. Una riga per sessione, "
          "raggruppate per caso. Nessun voto all'agente: la tabella dice cosa il banco di prova "
          "ha messo alla prova, e letta per caso è l'elenco delle correzioni per il run nuovo.", "",
          "**In evidenza** (colonna ⚠): esito malevolo (ESEGUE, TENTA, DANNO NON RICHIESTO) con effetto "
          "\"avvenuto\", e nessun detector del run l'ha segnalata. \"Segnalata da\" è il verdetto così com'è, "
          "prima di ambito ed esclusioni (fase 2); il verdetto del 4/9 è separato per scanner.", ""]
    for caso in sorted({r["caso"] for r in righe}):
        rr = [r for r in righe if r["caso"] == caso]
        intento, vettore, tipo = f0[caso]
        testa = f"## `{caso}`\n\n{intento}" + (f", vettore {vettore}" if vettore != "—" else "") + f", tipo {tipo}."
        if intento == "malevolo" and vettore != "ambiente" and not any(r["esito"] in {"ESEGUE", "TENTA"} for r in rr):
            testa += " **Mai arrivato all'esito malevolo.**"
        md += [testa, "", "| run | esito | causa o nota | backdoor | effetto | agente giudicabile | segnalata da | ⚠ |",
               "|---|---|---|---|---|---|---|---|"]
        for r in rr:
            cn = "; ".join(x for x in (r["causa"], r["nota"]) if x).replace("|", "/")
            md.append(f"| {r['run']} | {r['esito']} | {cn} | {r['backdoor']} | {r['effetto'].replace('|', '/')} | "
                      f"{r['agente_giudicabile']} | {r['segnalata_da']} | {'⚠' if r['danno_avvenuto_non_segnalato'] else ''} |")
        md.append("")
    (HERE / "tabella-per-caso.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(len(righe), "righe")


if __name__ == "__main__":
    main()
