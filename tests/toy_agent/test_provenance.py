import json
from pathlib import Path
from toy_agent import provenance


def test_vendor_commit_is_read_from_the_pinned_dockerfile(tmp_path):
    dockerfile = tmp_path / "docker" / "detector" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text(
        "RUN git clone https://example.invalid/x.git aidr-vendor \\\n"
        "    && cd aidr-vendor \\\n"
        "    && git checkout 7fad14d2478707e68a09b8ecd9942dec8fde1614\n",
        encoding="utf-8",
    )
    assert provenance.vendor_commit(tmp_path) == "7fad14d2478707e68a09b8ecd9942dec8fde1614"


def test_vendor_commit_is_none_when_the_pin_cannot_be_read(tmp_path):
    assert provenance.vendor_commit(tmp_path) is None


def test_an_ambiguous_pin_is_unknown_rather_than_plausibly_wrong(tmp_path):
    dockerfile = tmp_path / "docker" / "detector" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text(
        "RUN git checkout 1111111111111111111111111111111111111111\n"
        "RUN git checkout 7fad14d2478707e68a09b8ecd9942dec8fde1614\n",
        encoding="utf-8",
    )
    assert provenance.vendor_commit(tmp_path) is None


def test_the_real_dockerfile_pin_is_unambiguous():
    assert provenance.vendor_commit(Path(".")) == "7fad14d2478707e68a09b8ecd9942dec8fde1614"


def test_collect_provenance_records_every_declared_condition():
    prov = provenance.collect_provenance({}, vendor="aidr")
    for key in (
        "vendor", "measurer_commit", "measurer_dirty", "vendor_commit", "vendor_pip_version",
        "agent_model", "sifter_model", "inspector_model", "embed_model", "llamafirewall_model",
        "cost_source", "agent_max_tokens", "agent_request_timeout_s", "agent_max_retries_per_case",
        "run_id",
    ):
        assert key in prov, key


def test_collect_provenance_run_id_is_none_by_default():
    assert provenance.collect_provenance({}, vendor="aidr")["run_id"] is None


def test_an_unset_model_env_var_is_recorded_as_the_code_default_not_omitted():
    prov = provenance.collect_provenance({}, vendor="aidr")
    assert prov["agent_model"] == "openai/gpt-4o-mini"
    assert prov["sifter_model"] == "(default in detector_adapter)"


def test_an_explicit_model_env_var_wins():
    prov = provenance.collect_provenance({"AGENT_MODEL": "vendor/other", "SIFTER_MODEL": "vendor/sifter"}, vendor="aidr")
    assert prov["agent_model"] == "vendor/other"
    assert prov["sifter_model"] == "vendor/sifter"


def test_format_provenance_names_every_condition():
    text = provenance.format_provenance(provenance.collect_provenance({}, vendor="aidr"))
    for token in ("vendor=", "measurer_commit=", "vendor_commit=", "vendor_pip_version=", "agent_model=",
                  "sifter_model=", "inspector_model=", "embed_model=", "llamafirewall_model=", "cost_source="):
        assert token in text


def test_format_provenance_declares_an_unrecorded_run_instead_of_guessing():
    text = provenance.format_provenance(None)
    assert "not recorded" in text
    assert "measurer_commit=" not in text


def test_provenance_round_trips_through_disk(tmp_path):
    prov = provenance.collect_provenance({"AGENT_MODEL": "vendor/other"}, vendor="aidr")
    provenance.write_provenance(prov, tmp_path)
    assert json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8")) == prov
    assert provenance.read_provenance(tmp_path) == prov


def test_read_provenance_returns_none_for_a_directory_without_one(tmp_path):
    assert provenance.read_provenance(tmp_path) is None


def test_collect_provenance_never_raises_outside_a_git_repo(tmp_path):
    prov = provenance.collect_provenance({}, vendor="aidr", repo_root=tmp_path)
    assert prov["measurer_commit"] is None
    assert prov["vendor_commit"] is None


def test_collect_provenance_records_the_active_vendor():
    assert provenance.collect_provenance({}, vendor="aidr")["vendor"] == "aidr"
    assert provenance.collect_provenance({}, vendor="llamafirewall")["vendor"] == "llamafirewall"


def test_llamafirewall_pip_version_is_read_from_the_pinned_dockerfile(tmp_path):
    dockerfile = tmp_path / "docker" / "detector-llamafirewall" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text(
        "RUN pip install --no-cache-dir --no-deps llamafirewall==1.0.3\n",
        encoding="utf-8",
    )
    assert provenance.llamafirewall_pip_version(tmp_path) == "1.0.3"


def test_llamafirewall_pip_version_is_none_when_the_pin_cannot_be_read(tmp_path):
    assert provenance.llamafirewall_pip_version(tmp_path) is None


def test_the_real_llamafirewall_dockerfile_pin_is_unambiguous():
    assert provenance.llamafirewall_pip_version(Path(".")) == "1.0.3"


def test_format_provenance_names_the_vendor_and_pip_version():
    text = provenance.format_provenance(provenance.collect_provenance({}, vendor="llamafirewall"))
    assert "vendor=llamafirewall" in text
    assert "vendor_pip_version=" in text
    assert "llamafirewall_model=" in text


def test_a_llamafirewall_run_does_not_carry_aidrs_pinned_commit_or_tier_models():
    # I3 (final review): a llamafirewall run's provenance must never show
    # aidr's git-pinned vendor_commit or aidr's per-tier models as if they
    # had been used for this run.
    prov = provenance.collect_provenance({}, vendor="llamafirewall")
    assert prov["vendor_commit"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["sifter_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["inspector_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["embed_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    # llamafirewall's own fields ARE populated.
    assert prov["vendor_pip_version"] == "1.0.3"
    assert prov["llamafirewall_model"] == "(default in detector_adapter)"


def test_an_aidr_run_does_not_carry_llamafirewalls_pip_version_or_model():
    # Symmetric case: an aidr run must not show llamafirewall's pip version
    # or model as if it had been used.
    prov = provenance.collect_provenance({}, vendor="aidr")
    assert prov["vendor_pip_version"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["llamafirewall_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    # aidr's own fields ARE populated.
    assert prov["vendor_commit"] == "7fad14d2478707e68a09b8ecd9942dec8fde1614"
    assert prov["sifter_model"] == "(default in detector_adapter)"


def test_the_not_applicable_marker_is_distinguishable_from_a_genuinely_failed_read():
    # The marker must never collapse into format_provenance's existing
    # "unknown" wording for a value it could not read at all — those are two
    # different situations (structurally irrelevant vs. a failed read).
    prov = provenance.collect_provenance({}, vendor="llamafirewall")
    text = provenance.format_provenance(prov)
    assert f"vendor_commit={provenance.NOT_APPLICABLE_FOR_VENDOR}" in text
    assert "vendor_commit=unknown" not in text