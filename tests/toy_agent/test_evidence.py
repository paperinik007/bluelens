from toy_agent.evidence import collect_case_evidence, collect_thin_proxy_log


class FakeRunner:
    def __init__(self, responses: dict[tuple, bytes]):
        self._responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str]) -> bytes:
        self.calls.append(cmd)
        key = tuple(cmd)
        if key not in self._responses:
            raise AssertionError(f"unscripted command: {cmd}")
        return self._responses[key]


def _ps_key(service: str) -> tuple:
    return ("docker", "compose", "ps", "-q", service)


def test_collect_case_evidence_writes_all_channels_for_both_services(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"agent log line\n",
        ("docker", "compose", "logs", "--no-color", "detector"): b"detector log line\n",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"proxy log line\n",
        _ps_key("agent"): b"abc123\n",
        _ps_key("detector"): b"def456\n",
        ("docker", "diff", "abc123"): b"C /opt\n",
        ("docker", "diff", "def456"): b"C /var/log/vendor_proxy.jsonl\n",
        ("docker", "stats", "--no-stream", "abc123"): b"agent stats\n",
        ("docker", "stats", "--no-stream", "def456"): b"detector stats\n",
    })

    written = collect_case_evidence("case_001", ("agent", "detector"), tmp_path, run_command=runner)

    case_dir = tmp_path / "case_001"
    assert (case_dir / "agent.logs.txt").read_bytes() == b"agent log line\n"
    assert (case_dir / "detector.logs.txt").read_bytes() == b"detector log line\n"
    assert (case_dir / "egress-proxy.logs.txt").read_bytes() == b"proxy log line\n"
    assert (case_dir / "agent.diff.txt").read_bytes() == b"C /opt\n"
    assert (case_dir / "detector.diff.txt").read_bytes() == b"C /var/log/vendor_proxy.jsonl\n"
    assert (case_dir / "agent.stats.txt").read_bytes() == b"agent stats\n"
    assert (case_dir / "detector.stats.txt").read_bytes() == b"detector stats\n"
    assert set(written) == {
        "agent.logs", "detector.logs", "egress-proxy.logs",
        "agent.diff", "detector.diff", "agent.stats", "detector.stats",
    }


def test_collect_case_evidence_is_attributed_to_the_given_case_id(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"",
        ("docker", "compose", "logs", "--no-color", "detector"): b"",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"",
        _ps_key("agent"): b"abc123\n", _ps_key("detector"): b"def456\n",
        ("docker", "diff", "abc123"): b"", ("docker", "diff", "def456"): b"",
        ("docker", "stats", "--no-stream", "abc123"): b"", ("docker", "stats", "--no-stream", "def456"): b"",
    })
    collect_case_evidence("case_002", ("agent", "detector"), tmp_path, run_command=runner)
    assert (tmp_path / "case_002").is_dir()
    assert not (tmp_path / "case_001").exists()


def test_collect_case_evidence_skips_diff_and_stats_when_container_id_is_empty(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"",
        ("docker", "compose", "logs", "--no-color", "detector"): b"",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"",
        _ps_key("agent"): b"",  # container unreachable — no lines on stdout
        _ps_key("detector"): b"def456\n",
        ("docker", "diff", "def456"): b"C /var/log/vendor_proxy.jsonl\n",
        ("docker", "stats", "--no-stream", "def456"): b"detector stats\n",
    })

    written = collect_case_evidence("case_004", ("agent", "detector"), tmp_path, run_command=runner)

    assert "agent.diff" not in written
    assert "agent.stats" not in written
    assert not (tmp_path / "case_004" / "agent.diff.txt").exists()
    assert not (tmp_path / "case_004" / "agent.stats.txt").exists()
    assert "detector.diff" in written
    assert "detector.stats" in written


def test_collect_thin_proxy_log_scrubs_the_api_key(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector", "cat", "/var/log/vendor_proxy.jsonl"):
            b'{"port": 8100, "request": {}, "response": {}}\nsecret-key-value-embedded-here\n',
    })
    path = collect_thin_proxy_log(
        "case_003", tmp_path, "secret-key-value-embedded-here",
        service="detector", log_path="/var/log/vendor_proxy.jsonl", run_command=runner,
    )
    content = path.read_text(encoding="utf-8")
    assert "secret-key-value-embedded-here" not in content
    assert "[REDACTED]" in content
    assert path == tmp_path / "case_003" / "detector.vendor_proxy.jsonl"


def test_collect_thin_proxy_log_uses_the_given_service_and_container_path(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector-llamafirewall", "cat", "/var/log/llamafirewall_proxy.jsonl"):
            b'{"request": {}, "response": {}}\n',
    })
    path = collect_thin_proxy_log(
        "case_005", tmp_path, "sk-test",
        service="detector-llamafirewall", log_path="/var/log/llamafirewall_proxy.jsonl", run_command=runner,
    )
    assert path == tmp_path / "case_005" / "detector-llamafirewall.vendor_proxy.jsonl"


def test_collect_thin_proxy_log_names_the_output_file_after_the_service(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector-llamafirewall", "cat", "/var/log/llamafirewall_proxy.jsonl"): b"",
    })
    path = collect_thin_proxy_log(
        "case_006", tmp_path, "", service="detector-llamafirewall",
        log_path="/var/log/llamafirewall_proxy.jsonl", run_command=runner,
    )
    assert path.name == "detector-llamafirewall.vendor_proxy.jsonl"
