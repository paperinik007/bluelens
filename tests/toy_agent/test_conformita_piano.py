"""I tre controlli della matrice di conformita (`conformita_piano.py`): la citazione del piano c'e ancora, i test nominati esistono,
e nessuna voce numerata delle parti del piano che dicono come si passa dai verdetti ai numeri resta senza regola o senza una ragione scritta."""
import ast
import re
from pathlib import Path

import pytest

from conformita_piano import ESCLUSE, PIANO, REGOLE

REPO = Path(__file__).resolve().parents[2]
TESTI = REPO / "tests" / "toy_agent"


def _norm(testo: str) -> str:
    return re.sub(r"\s+", " ", testo).strip()


PIANO_RIGHE = (REPO / PIANO).read_text(encoding="utf-8").splitlines()
PIANO_NORM = _norm("\n".join(PIANO_RIGHE))


def _nomi_dei_test() -> set[str]:
    nomi: set[str] = set()
    for f in TESTI.glob("test_*.py"):
        for nodo in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                nomi.add(nodo.name)
    return nomi


NOMI = _nomi_dei_test()


def test_the_rule_ids_are_unique():
    ids = [r.id for r in REGOLE]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("r", REGOLE, ids=lambda r: r.id)
def test_the_quote_of_each_rule_is_still_in_the_plan_exactly_once(r):
    n = PIANO_NORM.count(_norm(r.citazione))
    assert n == 1, f"{r.id} ({r.sezione}): la citazione compare {n} volte nel piano: {r.citazione!r}. Il piano e cambiato: rileggere la regola."


@pytest.mark.parametrize("r", REGOLE, ids=lambda r: r.id)
def test_each_rule_is_either_proven_by_existing_tests_or_has_its_reason_written(r):
    assert r.stato in ("implementata", "rinviata", "procedurale")
    if r.stato == "implementata":
        assert r.test, f"{r.id}: regola implementata senza nessun test"
        mancanti = [t for t in r.test if t not in NOMI]
        assert not mancanti, f"{r.id}: test che non esistono: {mancanti}"
    else:
        assert r.nota and not r.test, f"{r.id}: una regola {r.stato} dice perche e non ha test"


# ---- completezza: ogni voce numerata delle parti che dicono come si va dai verdetti ai numeri ----

INIZIO = "## 13. Analisi e lettura dei risultati"
FINE = "## Controlli sul piano"
VOCE = re.compile(r"^( {0,6})(\d+b?)\.\s")
SOTTOVOCE = re.compile(r"^ {3}([a-f])\)\s")


def _voci() -> list[tuple[str, str, str]]:
    """(titolo della sezione, etichetta della voce, testo normalizzato della voce) per le voci numerate tra INIZIO e FINE."""
    inizio = next(i for i, r in enumerate(PIANO_RIGHE) if r.startswith(INIZIO))
    fine = next(i for i, r in enumerate(PIANO_RIGHE) if i > inizio and r.startswith(FINE))
    voci: list[tuple[str, str, list[str]]] = []
    titolo = INIZIO
    for r in PIANO_RIGHE[inizio:fine]:
        if r.startswith("#"):
            titolo = r.lstrip("# ").strip()
            voci.append((titolo, "", []))
            continue
        m = VOCE.match(r) or SOTTOVOCE.match(r)
        if m:
            voci.append((titolo, m.group(2) if VOCE.match(r) else m.group(1), [r]))
        elif voci:
            voci[-1][2].append(r)
    return [(t, e, _norm("\n".join(righe))) for t, e, righe in voci if e]


def _esclusa(titolo: str, etichetta: str) -> bool:
    return any(titolo.startswith(p) and etichetta == e for (p, e) in ESCLUSE)


def test_every_numbered_item_of_the_counting_parts_has_a_rule_or_a_written_reason():
    citazioni = [_norm(r.citazione) for r in REGOLE]
    scoperte = []
    for titolo, etichetta, testo in _voci():
        if _esclusa(titolo, etichetta):
            continue
        if not any(c in testo for c in citazioni):
            scoperte.append(f"({titolo[:60]!r}, {etichetta!r}): {testo[:90]}")
    assert not scoperte, "voci del piano senza nessuna regola e senza esclusione motivata:\n" + "\n".join(scoperte)


def test_every_exclusion_names_a_real_item_and_a_reason():
    voci = _voci()
    for (prefisso, etichetta), ragione in ESCLUSE.items():
        assert ragione, f"esclusione senza ragione: {(prefisso, etichetta)}"
        assert any(t.startswith(prefisso) and e == etichetta for t, e, _ in voci), f"l'esclusione {(prefisso, etichetta)} non corrisponde a nessuna voce"
