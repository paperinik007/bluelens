"""Runs one judge on saved sessions, one verdict per call (pilot, plan part 9).

Each verdict is one `docker compose exec` of the judge's evaluate_case module with the session JSON on stdin.
The money spent is read from the proxy's log of the calls it forwarded (the cost the provider reported), added
to a ledger on disk, and the run stops BEFORE the next verdict could pass the ceiling. Saved verdicts are never
redone. toy_agent never imports detector_adapter (Gap 9): module names are duplicated here by name.

    python -m toy_agent.judge_sessions --judge alignmentcheck --sessions DIR --repeats 5 --out DIR \
        --ledger FILE --ceiling 2.5 [--ids FILE] [--compose-file F ...] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .orchestrator import CommandRunner, default_command_runner


@dataclass(frozen=True)
class JudgeConfig:
    service: str
    module: str
    log_path: Optional[str]  # the proxy's log of forwarded calls; None for a judge that costs nothing


CONFIGS = {
    "alignmentcheck": JudgeConfig("detector-llamafirewall", "detector_adapter.vendors.llamafirewall.evaluate_case",
                                  "/var/log/llamafirewall_proxy.jsonl"),
    "aidr": JudgeConfig("detector", "detector_adapter.vendors.aidr.evaluate_case", "/var/log/vendor_proxy.jsonl"),
    "promptguard": JudgeConfig("detector-llamafirewall", "detector_adapter.vendors.llamafirewall.evaluate_case_promptguard",
                               None),
}

DEFAULT_WORST_FIRST = 0.01  # dollars, assumed for the largest verdict until one has been paid for


def compose_command(compose_files: list[str], env_files: list[str]) -> list[str]:
    return (["docker", "compose"] + [part for f in env_files for part in ("--env-file", f)]
            + [part for f in compose_files for part in ("-f", f)])


def judge_config(name: str) -> JudgeConfig:
    if name not in CONFIGS:
        raise ValueError(f"unknown judge: {name!r}, expected one of {sorted(CONFIGS)}")
    return CONFIGS[name]


def cost_of_log(text: str) -> tuple[float, int, int]:
    """(dollars, calls, calls with no reported cost) from the lines of a proxy log. A call whose cost the provider
    did not report, or that failed, is counted as unknown: never as free."""
    cost, calls, unknown = 0.0, 0, 0
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or "request" not in entry:
            continue
        calls += 1
        reported = ((entry.get("response") or {}).get("usage") or {}).get("cost")
        if reported is None:
            unknown += 1
        else:
            cost += reported
    return cost, calls, unknown


class Ledger:
    """What has been spent so far, on disk, so a restart or another judge's run adds to the same total."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._load()

    def _load(self) -> None:
        """The file is the truth: another run (another judge) may have added to it since this one last looked."""
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.spent = data.get("spent_usd", 0.0)
        self.largest = data.get("largest_verdict_usd", 0.0)
        self.verdicts = data.get("verdicts", 0)
        self.by_judge = data.get("by_judge", {})

    def add(self, judge: str, cost: float) -> None:
        self._load()
        self.spent += cost
        self.largest = max(self.largest, cost)
        self.verdicts += 1
        self.by_judge[judge] = self.by_judge.get(judge, 0.0) + cost
        self.path.write_text(json.dumps({
            "spent_usd": self.spent, "largest_verdict_usd": self.largest, "verdicts": self.verdicts,
            "by_judge": self.by_judge}, indent=1), encoding="utf-8")

    def may_continue(self, ceiling: float, worst_first: float = DEFAULT_WORST_FIRST) -> bool:
        """True if the next verdict, even as costly as the largest so far, would still leave the total within the
        ceiling."""
        self._load()
        worst = self.largest if self.largest > 0 else worst_first
        return self.spent + worst <= ceiling


@dataclass(frozen=True)
class Task:
    session_id: str
    judge: str
    repeat: int
    session_path: Path
    out_path: Path


def plan_tasks(sessions: Path, judge: str, repeats: int, out: Path, ids: Optional[list[str]]) -> list[Task]:
    """Round by round (every session once, then every session again), so that stopping early leaves each
    session with the same number of verdicts. Verdicts already saved are skipped."""
    judge_config(judge)
    wanted = sorted(ids) if ids is not None else None
    paths = sorted(Path(sessions).glob("*.json"))
    if wanted is not None:
        by_id = {p.stem: p for p in paths}
        paths = [by_id[i] for i in wanted]
    tasks = []
    for repeat in range(1, repeats + 1):
        for path in paths:
            target = Path(out) / f"{path.stem}_{judge}_{repeat}.json"
            if not target.exists():
                tasks.append(Task(path.stem, judge, repeat, path, target))
    return tasks


def _log_lines(compose: list[str], cfg: JudgeConfig, run_command: CommandRunner) -> int:
    res = run_command(compose + ["exec", "-T", cfg.service, "sh", "-c", f"wc -l < {cfg.log_path} 2>/dev/null || echo 0"],
                      b"", 60.0)
    return int(res.stdout.decode().split()[0])


def run_one(task: Task, compose: list[str], ledger: Ledger, run_command: CommandRunner = default_command_runner,
            timeout_s: float = 300.0) -> bool:
    """One verdict. The cost of the attempt is added to the ledger even if the evaluation failed."""
    cfg = judge_config(task.judge)
    before = _log_lines(compose, cfg, run_command) if cfg.log_path else 0
    res = run_command(compose + ["exec", "-T", cfg.service, "python", "-m", cfg.module],
                      task.session_path.read_bytes(), timeout_s)
    cost, calls, unknown = 0.0, 0, 0
    if cfg.log_path:
        tail = run_command(compose + ["exec", "-T", cfg.service, "sh", "-c", f"tail -n +{before + 1} {cfg.log_path}"],
                           b"", 60.0)
        cost, calls, unknown = cost_of_log(tail.stdout.decode(errors="replace"))
    ledger.add(task.judge, cost)
    if res.returncode != 0 or res.timed_out or res.failed_to_start:
        # why it failed, so a failure is never just a count (the evaluation prints only exception class names)
        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        task.out_path.with_suffix(".fail.json").write_text(json.dumps({
            "session_id": task.session_id, "judge": task.judge, "repeat": task.repeat, "returncode": res.returncode,
            "timed_out": res.timed_out, "failed_to_start": res.failed_to_start, "cost_usd": cost,
            "stderr_tail": res.stderr.decode(errors="replace")[-2000:]}, indent=1), encoding="utf-8")
        return False
    verdict = json.loads(res.stdout.decode())
    task.out_path.parent.mkdir(parents=True, exist_ok=True)
    task.out_path.write_text(json.dumps({
        "session_id": task.session_id, "judge": task.judge, "repeat": task.repeat, "verdict": verdict,
        "cost_usd": cost, "calls": calls, "unknown_cost_calls": unknown}, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one judge on saved sessions, with a spending ceiling.")
    parser.add_argument("--judge", required=True, choices=sorted(CONFIGS))
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--ceiling", type=float, default=2.5)
    parser.add_argument("--ids", type=Path, default=None, help="file with one session id per line")
    parser.add_argument("--compose-file", action="append", default=[])
    parser.add_argument("--env-file", action="append", default=[], help="passed to docker compose (never printed)")
    parser.add_argument("--max-consecutive-failures", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ids = [line.strip() for line in args.ids.read_text(encoding="utf-8").splitlines() if line.strip()] if args.ids else None
    tasks = plan_tasks(args.sessions, args.judge, args.repeats, args.out, ids)
    ledger = Ledger(args.ledger)
    print(f"{len(tasks)} verdicts to do; spent so far {ledger.spent:.4f} of {args.ceiling}")
    if args.dry_run:
        return
    compose = compose_command(args.compose_file, args.env_file)
    done = failures = 0
    for task in tasks:
        if not ledger.may_continue(args.ceiling):
            print(f"STOP before the ceiling: spent {ledger.spent:.4f}, the next verdict could cost "
                  f"{ledger.largest:.4f}; {done} verdicts done in this run, {len(tasks) - done} left")
            return
        if run_one(task, compose, ledger):
            done, failures = done + 1, 0
        else:
            failures += 1
            print(f"FAILED {task.session_id} {task.judge} {task.repeat}")
            if failures >= args.max_consecutive_failures:
                print("STOP: too many failures in a row")
                return
    print(f"done: {done} verdicts; spent so far {ledger.spent:.4f}")


if __name__ == "__main__":
    main()
