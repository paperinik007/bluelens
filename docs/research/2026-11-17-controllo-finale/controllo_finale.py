"""Controllo finale esterno (preparato il 2026-11-17). Due fasi:

  prepara  costruisce il pacchetto dal commit HEAD (non dalla copia di lavoro) e lo scrive in --out. Lavora offline.
  lancia   manda il pacchetto a UN modello, fornitore fissato e registrato, nessun ripiego. Senza --si-lancia stampa la stima del caso
           peggiore e si ferma; con --si-lancia chiama il fornitore. Si rifiuta di partire se il caso peggiore supera --cap.

La chiave si legge da .env (AGENT_OPENROUTER_API_KEY) solo dentro il processo e non si stampa. Regole dell'esecuzione: README.md.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "e2325fb"  # l'ultimo stato che il council del 12 novembre ha visto, prima delle sue correzioni

DIFFERENZE = ["docs/design/2026-10-11-piano-run-v3.md", "docs/design/2026-11-05-limiti-dichiarati-run-v3.md",
              "dataset_v3/controls/README.md", "dataset_v3/condizioni_attese.json", "src/toy_agent/check_conditions.py",
              "src/toy_agent/run_card.py"]
PROGRAMMI = ["src/toy_agent/analisi_v3.py", "src/toy_agent/elenco_a.py", "src/toy_agent/registra_versioni.py"]
TEST = ["tests/toy_agent/test_analisi_v3.py", "tests/toy_agent/test_elenco_a.py", "tests/toy_agent/test_registra_versioni.py"]
GIA_VALUTATO = ["docs/research/2026-11-12-council-congelamento.md", "docs/research/2026-11-12-lettura-coerenza.md",
                "docs/research/2026-11-11-specialisti-congelamento/VALUTAZIONE-metodologia.md",
                "docs/research/2026-11-11-specialisti-congelamento/VALUTAZIONE-sicurezza-integrita.md",
                "docs/research/2026-11-12-prova-comandi-nuovi/ESITO.md"]

NOTA = ("NOTA SULL'ESECUZIONE: non hai accesso al repository e non hai strumenti. Le parti che seguono sono incollate per intero, ciascuna con "
        "il suo titolo e, dove serve, il percorso. Dove le istruzioni chiedono una PROVA, cita il documento e la sezione (o la funzione) oppure "
        "scrivi SOLO TESTO. Le sezioni sono, nell'ordine: DIFFERENZE, ELENCO A, PROGRAMMI NUOVI, NOMI DEI TEST, PIANO COMPLETO, PAGINA DEI "
        "LIMITI, PRINCIPI, GIÀ VALUTATO.\n")


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8")


def blob(percorso: str) -> str:
    return git("cat-file", "blob", f"HEAD:{percorso}")


def elenco_compatto(percorso: Path) -> str:
    x = json.loads(percorso.read_text(encoding="utf-8"))
    r = [f"Elenco A (BOZZA), generato il {x['data']} dal commit {x['commit_del_codice']}. Per ogni file l'elenco vero ha uno SHA-256 del contenuto "
         "committato e uno per gruppo: qui sono omessi, restano i nomi.", ""]
    for nome, g in x["gruppi"].items():
        r.append(f"## Gruppo {nome} ({len(g['file'])} file; dichiarato come: {', '.join(g['percorsi'])})")
        r += [f"- {f}" for f in g["file"]]
        r.append("")
    r.append("## Pin dei produttori (letti dai Dockerfile)")
    r += [f"- {k}: {v} (da {x['origine_dei_pin'][k]['file']})" for k, v in x["pin_dei_produttori"].items()]
    r.append("")
    if x.get("immagini"):
        r.append("## Immagini Docker registrate")
        for k, i in x["immagini"].items():
            stati = {}
            for f in i["file_copiati"].values():
                stati[f["rispetto_al_commit"]] = stati.get(f["rispetto_al_commit"], 0) + 1
            pip = "nessun pip freeze" if i["pip_freeze"] is None else f"pip freeze di {len(i['pip_freeze'])} righe"
            r.append(f"- {k}: {i['nome']}, identificativo {i['id']}, {pip}, {len(i['file_copiati'])} file copiati dentro, "
                     f"confronto con il commit: {stati}")
        r.append("")
    r.append("## Da registrare a mano (dichiarato nell'elenco)")
    r += [f"- {v}" for v in x["da_registrare_a_mano"]]
    return "\n".join(r)


def nomi_dei_test(percorso: str) -> str:
    nomi = [riga.split("(")[0].replace("def ", "").strip() for riga in blob(percorso).splitlines() if riga.startswith("def test_")]
    return f"{percorso}: {len(nomi)} test\n" + "\n".join(f"- {n}" for n in nomi)


def parti(elenco: Path) -> list[tuple[str, str]]:
    p = [("DIFFERENZE: git diff da " + BASE + " (testo visto dal council) a HEAD",
          git("diff", "--no-color", "-U3", BASE, "HEAD", "--", *DIFFERENZE)),
         ("ELENCO A (BOZZA, vista compatta)", elenco_compatto(elenco))]
    p += [(f"PROGRAMMI NUOVI: {f}", blob(f)) for f in PROGRAMMI]
    p += [("NOMI DEI TEST (il codice dei test non è incollato)", "\n\n".join(nomi_dei_test(t) for t in TEST))]
    p += [("PIANO COMPLETO a HEAD: docs/design/2026-10-11-piano-run-v3.md", blob("docs/design/2026-10-11-piano-run-v3.md")),
          ("PAGINA DEI LIMITI GIÀ DICHIARATI: docs/design/2026-11-05-limiti-dichiarati-run-v3.md",
           blob("docs/design/2026-11-05-limiti-dichiarati-run-v3.md")),
          ("PRINCIPI DEL PROGETTO: SPIRIT.md", blob("SPIRIT.md"))]
    p += [(f"GIÀ VALUTATO: {f}", blob(f)) for f in GIA_VALUTATO]
    return p


def prepara(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for nome in ("istruzione-sistema.md", "input-utente.md", "contenuto.json"):
        if (out / nome).exists():
            raise SystemExit(f"{out / nome} esiste gia: non si sovrascrive")
    sistema = (HERE / "istruzioni-controllo-finale.md").read_text(encoding="utf-8")
    ps = parti(Path(a.elenco))
    utente = NOTA + "".join(f"\n\n=== {titolo} ===\n{testo}" for titolo, testo in ps)
    (out / "istruzione-sistema.md").write_text(sistema, encoding="utf-8", newline="\n")
    (out / "input-utente.md").write_text(utente, encoding="utf-8", newline="\n")
    contenuto = {"commit": git("rev-parse", "HEAD").strip(), "base_delle_differenze": BASE,
                 "parti": [{"titolo": t, "caratteri": len(x), "sha256": hashlib.sha256(x.encode("utf-8")).hexdigest()} for t, x in ps]}
    (out / "contenuto.json").write_text(json.dumps(contenuto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    tot = len(sistema) + len(utente)
    print(f"pacchetto in {out}: {len(ps)} parti, {tot} caratteri, circa {round(tot / 3.5 / 1000)} mila token in ingresso")
    for t, x in ps:
        print(f"  {len(x):>8}  {t[:90]}")


def chiave() -> str:
    for riga in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if riga.startswith("AGENT_OPENROUTER_API_KEY="):
            return riga.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("chiave non trovata in .env")


def lancia(a) -> None:
    out = Path(a.out)
    sistema = (out / "istruzione-sistema.md").read_text(encoding="utf-8")
    utente = (out / "input-utente.md").read_text(encoding="utf-8")
    token_in = (len(sistema) + len(utente)) / 3.5
    peggiore = token_in * a.prezzo_in / 1e6 + a.max_output * a.prezzo_out / 1e6
    print(f"modello {a.modello}, fornitore {a.fornitore}: ingresso circa {round(token_in / 1000)} mila token, uscita al massimo {a.max_output}; "
          f"caso peggiore circa {peggiore:.2f} dollari (tetto {a.cap:.2f})")
    if peggiore > a.cap:
        raise SystemExit("STOP: il caso peggiore supera il tetto")
    if not a.si_lancia:
        print("NON lanciato: manca --si-lancia")
        return
    for nome in ("risposta.json", "output.md", "meta.json"):
        if (out / nome).exists():
            raise SystemExit(f"{out / nome} esiste gia: un solo giro, non si sovrascrive")
    corpo = {"model": a.modello, "max_tokens": a.max_output,
             "provider": {"order": [a.fornitore], "allow_fallbacks": False},
             "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": utente}]}
    if a.temperatura is not None:
        corpo["temperature"] = a.temperatura
    t0 = time.time()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(corpo).encode("utf-8"),
                                 headers={"Authorization": f"Bearer {chiave()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        resp = json.loads(r.read().decode("utf-8"))
    secondi = round(time.time() - t0, 1)
    (out / "risposta.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    testo = resp["choices"][0]["message"]["content"]
    (out / "output.md").write_text(f"# Controllo finale esterno ({resp.get('model')}, fornitore {resp.get('provider')})\n\n{testo}\n",
                                   encoding="utf-8", newline="\n")
    meta = {"model": resp.get("model"), "provider": resp.get("provider"), "id": resp.get("id"), "usage": resp.get("usage"), "secondi": secondi,
            "finish_reason": resp["choices"][0].get("finish_reason")}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8", newline="\n")
    print(meta)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    a = s.add_parser("prepara")
    a.add_argument("--out", required=True)
    a.add_argument("--elenco", required=True, help="il file dell'elenco A (bozza) generato da toy_agent.elenco_a")
    b = s.add_parser("lancia")
    b.add_argument("--out", required=True)
    b.add_argument("--modello", required=True)
    b.add_argument("--fornitore", required=True)
    b.add_argument("--prezzo-in", type=float, required=True, help="dollari per milione di token in ingresso")
    b.add_argument("--prezzo-out", type=float, required=True, help="dollari per milione di token in uscita")
    b.add_argument("--cap", type=float, required=True, help="tetto in dollari sul caso peggiore")
    b.add_argument("--max-output", type=int, default=30000)
    b.add_argument("--temperatura", type=float, default=None, help="omessa se non indicata (alcuni modelli non la accettano)")
    b.add_argument("--si-lancia", action="store_true", help="senza questo flag non parte nessuna chiamata")
    args = p.parse_args()
    (prepara if args.cmd == "prepara" else lancia)(args)


if __name__ == "__main__":
    sys.exit(main())
