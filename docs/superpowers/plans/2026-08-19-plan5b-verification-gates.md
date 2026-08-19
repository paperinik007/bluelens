# Plan 5b — Gate di verifica del dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrivere le 4 verifiche ancora assenti del design doc Plan 5 (mapping
Requisito→Verifica): il coverage gate bloccante sulle tecniche, l'anti-scorciatoia
tool→label bloccante, la coerenza catalogo↔dataset non bloccante, e la validazione del
template — chiudendo anche l'ultimo item aperto in `registro-limiti-aperti.md` che le
riguarda.

**Architecture:** Solo codice — 3 file di test nuovi/estesi più una piccola modifica a
`run_batch.py::main()`. **Indipendente da Plan 5a**: nessuno di questi task richiede che
il catalogo sia completo o che `dataset/` contenga `TestCase` reali — `load_dataset()` su
una directory vuota o inesistente restituisce `[]` senza sollevare eccezioni (verificato
in questa sessione), quindi il coverage gate (Task 1) è scrivibile e verificabile subito,
nello stato "rosso" corretto (fallisce elencando le tecniche mancanti, non per un errore
di importazione).

**Tech Stack:** Python 3, pytest.

**Spec:** `docs/design/2026-08-19-plan5-dataset-design.md` (mapping Requisito→Verifica),
`docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 17),
`docs/design/registro-limiti-aperti.md` (voce "Validazione template/case_id... non
riproducibile" — Task 4 la chiude).

## Global Constraints

- Il coverage gate (Task 1) e l'anti-scorciatoia (Task 2) sono **gate bloccanti**: il
  primo è un test pytest statico eseguibile prima di `run_batch.py`; il secondo è un
  controllo in-process **dentro** `run_batch.py::main()`, tra `execute_batch()` e la
  scrittura di `report.md` — non un test pytest. Precedente strutturale più vicino nel
  codice: `preflight_check_models` (`run_batch.py:125-129`, `sys.exit(1)` prima di
  procedere).
- Il coverage gate verifica **12 tecniche**, non 14: `{T0001..T0014} - {T0009, T0011}`
  (Gap 17, limite dichiarato — mai un `== 14` silenzioso).
- La coerenza catalogo↔dataset (Task 3) e la validazione template (Task 4) sono test
  pytest **non bloccanti** (fanno parte della suite normale, non condizionano
  l'esecuzione di `run_batch.py`).
- Nessuna di queste verifiche importa o richiede contenuto reale in `dataset/` per
  esistere — possono essere scritte e committate prima, durante o dopo Plan 5a/5c.

---

## Task 1: Coverage gate — 12 delle 14 tecniche coperte da almeno un `TestCase` malevolo

**Files:**
- Create: `tests/test_dataset_coverage.py`

**Interfaces:**
- Consumes: `toy_agent.dataset.load_dataset` (esistente, `dataset.py:53`),
  `catalog/vendor_taxonomy_snapshot.yaml` (esistente).
- Produces: nessuna nuova interfaccia — un test pytest statico. Consumato da Plan 5d
  (deve passare prima che `run_batch.py` giri sul dataset completo).

- [ ] **Step 1: Scrivi il test**

```python
# tests/test_dataset_coverage.py
"""Blocking coverage gate (design doc Plan 5, mapping Requisito -> Verifica):
the set of technique_target values on malicious TestCase entries in dataset/
must cover every T-code in the vendor taxonomy except the two declared as
out of scope this round (Gap 17) — never a silent `== 14`.

Static and pytest-collectible, unlike the tool->label shortcut check
(run_batch.py::main(), Task 2 of this plan): every malicious TestCase
declares technique_target up front, at authoring time — no live execution
needed to know what this test should check.
"""

from pathlib import Path

import yaml

from toy_agent.dataset import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
TAXONOMY_PATH = REPO_ROOT / "catalog" / "vendor_taxonomy_snapshot.yaml"

# Gap 17 (docs/design/2026-08-14-toy-agent-gap-tracking.md): no scenario for
# these two was found that doesn't risk contaminating benign cases sharing
# the same tool. Declared limitation, not a silent gap — remove an entry
# here only after Gap 17 is actually resolved in the gap-tracking doc.
DECLARED_UNCOVERED_TECHNIQUES = {"T0009", "T0011"}


def _all_vendor_techniques() -> set[str]:
    data = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return set(data["techniques"].keys())


def test_every_non_excluded_technique_has_a_malicious_test_case():
    required = _all_vendor_techniques() - DECLARED_UNCOVERED_TECHNIQUES
    cases = load_dataset(DATASET_DIR)
    covered = {c.technique_target for c in cases if c.label == "malicious"}
    missing = required - covered
    assert not missing, (
        f"no malicious TestCase in dataset/ declares technique_target for: "
        f"{sorted(missing)} — every technique except {sorted(DECLARED_UNCOVERED_TECHNIQUES)} "
        f"(Gap 17) must be covered before run_batch.py runs on the full dataset"
    )
```

- [ ] **Step 2: Esegui il test, verifica che fallisca nel modo corretto**

Run: `python -m pytest tests/test_dataset_coverage.py -v`
Expected: FAIL — `AssertionError` che elenca 12 tecniche mancanti (`dataset/` non esiste
ancora o è vuota in questo momento del piano). **Non** deve fallire con un errore di
importazione o un'eccezione diversa da `AssertionError` — se fallisce diversamente,
`load_dataset`/`yaml.safe_load` hanno un problema da correggere prima di continuare.

- [ ] **Step 3: Commit**

Questo test resta rosso finché Plan 5c non popola `dataset/` — è lo stato atteso, non un
bug. Committalo comunque: è la rete di sicurezza che Plan 5d userà per decidere se può
procedere.

```bash
git add tests/test_dataset_coverage.py
git commit -m "test: add blocking coverage gate for 12/14 techniques (Gap 17 exception declared)"
```

---

## Task 2: Anti-scorciatoia tool→label — controllo in-process in `run_batch.py::main()`

**Files:**
- Modify: `src/toy_agent/run_batch.py`
- Test: `tests/toy_agent/test_run_batch.py`

**Interfaces:**
- Consumes: `BatchResult.metric_cases` (esistente, `sequence.py:108` — i `TestCase` con
  `transcript` realmente osservato, non il turno seed autorato).
- Produces: `find_malicious_only_tools(cases: list[TestCase]) -> set[str]`, esportata da
  `run_batch.py`, usata da `main()`.

- [ ] **Step 1: Scrivi il test per `find_malicious_only_tools`**

```python
# tests/toy_agent/test_run_batch.py — aggiungi in fondo al file

from toy_agent.schema import ToolCall


def _case_with_tool_call(case_id, label, tool_name, technique_target=None):
    transcript = Transcript(
        session_id=case_id,
        turns=[
            Turn(seq=0, role="user", content="hi"),
            Turn(
                seq=1, role="tool", content="ok",
                tool_call=ToolCall(tool_name=tool_name, arguments={}, result="ok", status="ok"),
            ),
        ],
    )
    return TestCase(case_id=case_id, label=label, technique_target=technique_target, rationale="r", transcript=transcript)


def test_find_malicious_only_tools_flags_a_tool_seen_only_in_malicious_cases():
    cases = [
        _case_with_tool_call("c1", "malicious", "bulk_export", technique_target="T0012"),
        _case_with_tool_call("c2", "benign", "query_customer_db"),
    ]
    assert run_batch.find_malicious_only_tools(cases) == {"bulk_export"}


def test_find_malicious_only_tools_ignores_a_tool_also_seen_in_a_benign_case():
    cases = [
        _case_with_tool_call("c1", "malicious", "update_account", technique_target="T0005"),
        _case_with_tool_call("c2", "benign", "update_account"),
    ]
    assert run_batch.find_malicious_only_tools(cases) == set()


def test_find_malicious_only_tools_skips_cases_with_no_transcript():
    dataset = [_ground_truth("c1", label="malicious", technique_target="T0001")]
    dataset[0].transcript = None
    assert run_batch.find_malicious_only_tools(dataset) == set()


def test_main_refuses_to_write_the_report_when_a_tool_appears_only_in_malicious_cases(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        malicious_case = _case_with_tool_call("c1", "malicious", "bulk_export", technique_target="T0012")
        verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="malicious", technique_detected="T0012")
        return BatchResult(
            cases=[malicious_case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[malicious_case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1
    assert not (run_output_dir / "report.md").exists()
```

- [ ] **Step 2: Esegui i test, verifica che falliscano**

Run: `python -m pytest tests/toy_agent/test_run_batch.py -k "malicious_only_tools or refuses_to_write" -v`
Expected: FAIL — `AttributeError: module 'toy_agent.run_batch' has no attribute 'find_malicious_only_tools'` (non esiste ancora).

- [ ] **Step 3: Implementa `find_malicious_only_tools` e collegala a `main()`**

In `src/toy_agent/run_batch.py`, aggiungi la funzione (dopo `_setup_notes`, prima di
`main`):

```python
def find_malicious_only_tools(cases: list[TestCase]) -> set[str]:
    """Tool names that appear only in malicious cases' observed transcripts,
    never in a benign one — the tool->label correlation shortcut a detector
    could exploit instead of reasoning about content (design doc, mapping
    Requisito -> Verifica; Gap 7 risk 1, generalized to all 14 techniques).

    Reads case.transcript.turns[*].tool_call.tool_name from the REAL
    transcript observed after execution (metric_cases), never the authored
    seed turn — what tools a TestCase actually exercises is not knowable
    before the agent runs (design doc: this check cannot be a static test on
    the dataset, unlike the coverage gate)."""
    tools_by_label: dict[str, set[str]] = {"malicious": set(), "benign": set()}
    for case in cases:
        if case.transcript is None:
            continue
        for turn in case.transcript.turns:
            if turn.tool_call is not None:
                tools_by_label.setdefault(case.label, set()).add(turn.tool_call.tool_name)
    return tools_by_label.get("malicious", set()) - tools_by_label.get("benign", set())
```

Poi, in `main()`, subito dopo la riga `result = execute_batch(...)` e prima di
`metrics = compute_metrics(...)`:

```python
    result = execute_batch(dataset, run_output_dir, container_lifecycle=parsed.container_lifecycle, api_key=api_key)

    shortcut_tools = find_malicious_only_tools(result.metric_cases)
    if shortcut_tools:
        print(
            f"tool->label shortcut check failed: tool(s) {sorted(shortcut_tools)} appear only in "
            f"malicious metric_cases this run — refusing to write report.md (design doc, mapping "
            f"Requisito -> Verifica, anti-shortcut gate)",
            file=sys.stderr,
        )
        sys.exit(1)

    metrics = compute_metrics(result.metric_cases, result.metric_verdicts)
```

- [ ] **Step 4: Esegui i test, verifica che passino**

Run: `python -m pytest tests/toy_agent/test_run_batch.py -v`
Expected: PASS — inclusa l'intera suite esistente di `test_run_batch.py` (nessuna
regressione sui test già presenti che non innescano mai la scorciatoia, perché i loro
`TestCase` non hanno `tool_call` nel transcript).

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/run_batch.py tests/toy_agent/test_run_batch.py
git commit -m "feat: block report.md when a tool appears only in malicious metric_cases (anti-shortcut gate)"
```

---

## Task 3: Coerenza catalogo↔dataset dopo la selezione

**Files:**
- Modify: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `_load_entries` (esistente, `test_catalog.py:28`), `toy_agent.dataset.load_dataset`.
- Produces: nessuna nuova interfaccia — 1 test pytest non bloccante, aggiunto alla suite
  esistente del catalogo.

- [ ] **Step 1: Scrivi il test**

```python
# tests/test_catalog.py — aggiungi in fondo al file

from toy_agent.dataset import load_dataset

DATASET_PATH = Path(__file__).resolve().parent.parent / "dataset"


def test_selected_catalog_entries_match_their_dataset_test_case():
    """Non-blocking (design doc, mapping Requisito -> Verifica): every catalog
    entry with status: selected must still agree with the real TestCase it
    produced — no silent drift between catalog/cases.yaml and dataset/."""
    selected = [e for e in _load_entries() if e["status"] == "selected"]
    if not selected:
        return  # nothing selected yet — vacuously fine, not a false pass on real drift
    cases_by_id = {c.case_id: c for c in load_dataset(DATASET_PATH)}
    offending = []
    for entry in selected:
        case = cases_by_id.get(entry["selected_as"])
        if case is None:
            offending.append(f"{entry['catalog_id']}: selected_as {entry['selected_as']!r} not found in dataset/")
            continue
        if entry["label_hint"] == "malicious" and case.technique_target != entry["technique_code"]:
            offending.append(
                f"{entry['catalog_id']}: dataset technique_target {case.technique_target!r} "
                f"!= catalog technique_code {entry['technique_code']!r}"
            )
        if entry["catalog_id"] not in case.rationale:
            offending.append(f"{entry['catalog_id']}: dataset case {case.case_id!r} rationale does not mention the catalog_id")
    assert not offending, f"catalog/dataset drift: {offending}"
```

- [ ] **Step 2: Esegui il test, verifica che passi (vacuamente, nessuna voce `selected` ancora)**

Run: `python -m pytest tests/test_catalog.py::test_selected_catalog_entries_match_their_dataset_test_case -v`
Expected: PASS — nessuna voce `selected` in `catalog/cases.yaml` finché Plan 5c non
gira, quindi il test ritorna presto senza controllare nulla. Questo è corretto (non un
falso positivo mascherato): il test diventerà significativo solo quando Plan 5c
selezionerà le prime voci.

- [ ] **Step 3: Commit**

```bash
git add tests/test_catalog.py
git commit -m "test: check catalog/dataset consistency for selected entries (non-blocking)"
```

---

## Task 4: Validazione template — chiude l'item aperto in `registro-limiti-aperti.md`

**Files:**
- Modify: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `toy_agent.dataset._entry_to_test_case` (esistente, `dataset.py:21` — non
  pubblica per convenzione di modulo, ma già usata da `load_dataset`; importarla
  direttamente per questo test è la stessa scelta implicita già fatta da
  `test_run_batch.py`, che importa e testa funzioni interne del pacchetto).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_catalog.py — aggiungi in fondo al file

from toy_agent.dataset import _entry_to_test_case


def _filled_template_example(label: str, technique_target: str | None) -> dict:
    """A realistic filled-in copy of catalog/_template.yaml's field set —
    not a parse of the template file itself (its placeholder values, e.g.
    <mechanic_descriptive_slug>, would never pass CASE_ID_PATTERN). Closes
    the open item in registro-limiti-aperti.md: the design doc's claim that
    the template compiles into a valid TestCase was verified by hand,
    leaving no trace in the repo — this test makes it a re-runnable fact."""
    case_id = "template_validation_" + label + "_example"
    return {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": "Template validation example, not part of the real dataset — see registro-limiti-aperti.md.",
        "transcript": {
            "session_id": case_id,
            "turns": [{"seq": 0, "role": "user", "content": "example seed content", "tool_call": None}],
            "stop_reason": None,
        },
    }


def test_template_compiled_with_a_malicious_example_produces_a_valid_test_case():
    data = _filled_template_example("malicious", "T0001")
    case = _entry_to_test_case(data, Path("template_validation_malicious_example.yaml"))
    assert case.label == "malicious"
    assert case.technique_target == "T0001"


def test_template_compiled_with_a_benign_example_produces_a_valid_test_case():
    data = _filled_template_example("benign", None)
    case = _entry_to_test_case(data, Path("template_validation_benign_example.yaml"))
    assert case.label == "benign"
    assert case.technique_target is None


def test_template_validation_actually_catches_a_real_error():
    """Negative check (design doc self-review discipline): a validation test
    that never fails on bad input is vacuous. A benign entry declaring a
    technique_target is exactly the mistake TestCase.__post_init__ already
    rejects (schema.py) — confirm _entry_to_test_case surfaces it, not just
    that valid input passes."""
    data = _filled_template_example("benign", "T0001")
    try:
        _entry_to_test_case(data, Path("bad_example.yaml"))
        assert False, "expected ValueError for a benign entry declaring technique_target"
    except ValueError:
        pass
```

- [ ] **Step 2: Esegui i test, verifica che passino**

Run: `python -m pytest tests/test_catalog.py -k template_validation -v`
Expected: PASS su tutti e 3 — se falliscono, `_entry_to_test_case`/`TestCase` hanno un
comportamento diverso da quanto documentato nel design doc, da investigare prima di
continuare (non un placeholder da aggiustare qui).

- [ ] **Step 3: Rimuovi l'item da `registro-limiti-aperti.md`**

In `docs/design/registro-limiti-aperti.md`, elimina il paragrafo "Validazione
template/case_id del design doc Plan 5 non riproducibile" dalla sezione "Aperti" — la
risoluzione (questo commit) diventa il record, per la convenzione dichiarata in cima al
file.

- [ ] **Step 4: Commit**

```bash
git add tests/test_catalog.py docs/design/registro-limiti-aperti.md
git commit -m "test: validate catalog/_template.yaml's field set compiles to a real TestCase (closes open finding)"
```

---

## Self-Review (svolto durante la scrittura di questo piano)

- **Copertura spec**: le 4 righe "non ancora scritto" del mapping Requisito→Verifica del
  design doc hanno ciascuna un task — Task 1 (coverage), Task 2 (anti-scorciatoia), Task
  3 (coerenza catalogo↔dataset), Task 4 (validazione template, anche voce del registro
  limiti aperti).
- **Placeholder scan**: nessun `TBD` — ogni test ha assert reali, ogni modifica di codice
  ha il diff letterale.
- **Coerenza tipi**: `find_malicious_only_tools` usa `TestCase`/`ToolCall` esistenti
  (`schema.py`), nessuna firma nuova introdotta altrove nel piano che diverga da questa.
- **Indipendenza da Plan 5a/5c**: verificato esplicitamente (vedi "Architecture" sopra)
  che nessun task di questo piano richiede contenuto reale in `dataset/` per essere
  scritto e passato nel proprio stato atteso (rosso per Task 1, verde vacuo per Task 3).
