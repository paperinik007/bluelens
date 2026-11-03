"""The third-party integration server for aidr (plan part 2, correction 1; permissions table, entries 10 and
"revisione dello specialista" rule 6): present in every session under the same name, with the same entry in the
SourceLens registry whichever of its four versions the session used; the version the session used is what aidr
can read. Nothing in the name, the registry or the file name tells the versions apart."""
import hashlib
from pathlib import Path

import pytest

from detector_adapter.vendors.aidr.adapter import (
    HALVARD_REGISTRY_PATH,
    HALVARD_VERSIONS,
    SERVER_NAME,
    THIRD_PARTY_SERVER,
    install_server_version,
    server_for_tool,
    third_party_version,
)

REPO = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO / "dataset_v3" / "servers" / "halvard_crm"

# these read the repo's own files, which are not in the detector container
pytestmark = pytest.mark.skipif(not VERSIONS_DIR.is_dir(), reason="the repo files are not in the detector container")


def _lf(path):
    return path.read_bytes().replace(b"\r\n", b"\n")


def test_the_integrations_own_tool_belongs_to_its_server_and_every_other_tool_to_the_support_server():
    assert server_for_tool("crm_sync_contact") == THIRD_PARTY_SERVER == "halvard_crm"
    assert server_for_tool("update_account") == SERVER_NAME == "support"
    assert server_for_tool("bulk_export") == "support"


def test_a_session_names_its_version_and_a_session_without_one_uses_the_honest_version():
    assert third_party_version({"session_id": "s", "third_party_version": "compromised_data"}) == "compromised_data"
    assert third_party_version({"session_id": "s"}) == "honest"


def test_an_unknown_version_is_refused():
    with pytest.raises(ValueError, match="unknown third-party version"):
        third_party_version({"session_id": "s", "third_party_version": "backdoored"})


def test_there_is_one_version_file_for_each_known_version():
    for version in HALVARD_VERSIONS:
        assert (VERSIONS_DIR / f"{version}.py").is_file()
    assert sorted(p.stem for p in VERSIONS_DIR.glob("*.py")) == sorted(HALVARD_VERSIONS)


def test_the_known_versions_are_the_ones_the_agent_side_knows():
    halvard = pytest.importorskip("toy_agent.halvard", reason="toy_agent is not installed in the detector container")
    assert tuple(HALVARD_VERSIONS) == tuple(halvard.THIRD_PARTY_VERSIONS)


def test_installing_a_version_puts_exactly_its_code_at_the_registered_path_and_returns_its_hash(tmp_path):
    target = tmp_path / "servers" / HALVARD_REGISTRY_PATH
    digest = install_server_version("compromised_permissions", VERSIONS_DIR, target)
    expected = _lf(VERSIONS_DIR / "compromised_permissions.py")
    assert target.read_bytes() == expected
    assert digest == hashlib.sha256(expected).hexdigest()


def test_the_installed_code_and_its_hash_do_not_depend_on_the_line_endings_of_the_checkout(tmp_path):
    # git stores these files with LF (.gitattributes); a Windows checkout has CRLF. The hash in a verdict must be
    # the same on every machine, so the installed file always has LF.
    versions = tmp_path / "versions"
    versions.mkdir()
    (versions / "honest.py").write_bytes(b"line one\r\nline two\r\n")
    target = tmp_path / HALVARD_REGISTRY_PATH
    digest = install_server_version("honest", versions, target)
    assert target.read_bytes() == b"line one\nline two\n"
    assert digest == hashlib.sha256(b"line one\nline two\n").hexdigest()


def test_installing_another_version_replaces_the_previous_one(tmp_path):
    target = tmp_path / HALVARD_REGISTRY_PATH
    install_server_version("compromised_data", VERSIONS_DIR, target)
    install_server_version("honest", VERSIONS_DIR, target)
    assert target.read_bytes() == _lf(VERSIONS_DIR / "honest.py")


def test_installing_an_unknown_version_changes_nothing_and_says_so(tmp_path):
    target = tmp_path / HALVARD_REGISTRY_PATH
    install_server_version("honest", VERSIONS_DIR, target)
    with pytest.raises(ValueError, match="unknown third-party version"):
        install_server_version("backdoored", VERSIONS_DIR, target)
    assert target.read_bytes() == _lf(VERSIONS_DIR / "honest.py")


def test_the_registry_has_one_entry_for_the_integration_and_one_for_the_support_server():
    yaml = pytest.importorskip("yaml")
    servers = yaml.safe_load((REPO / "docker" / "detector" / "source_registry.yaml").read_text(encoding="utf-8"))["servers"]
    names = [s["name"] for s in servers]
    assert names.count("halvard_crm") == 1 and names.count("support") == 1
    entry = next(s for s in servers if s["name"] == "halvard_crm")
    assert entry["path"] == HALVARD_REGISTRY_PATH
    assert "toy_support" not in names  # two near-identical names for the clean server would show up in the listing


def test_nothing_in_a_version_file_says_what_it_is():
    # rule 6: the hidden behaviour is only in the code it does, not in a name, a comment or a word
    for path in VERSIONS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert "#" not in text, path.name
        for word in ("honest", "compromised", "malicious", "backdoor", "attack", "hidden", "exfiltrat"):
            assert word not in text, f"{path.name}: {word}"
