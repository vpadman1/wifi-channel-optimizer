import json
import stat
import sys
import pytest
from aliases import (
    load_aliases, save_aliases, set_alias, remove_alias, resolve, _normalize,
)


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / "aliases.json"


class TestNormalize:
    def test_uppercases_mac(self):
        assert _normalize("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"

    def test_strips_whitespace(self):
        assert _normalize("  aa:bb:cc:dd:ee:ff  ") == "AA:BB:CC:DD:EE:FF"


class TestLoadSave:
    def test_load_missing_file_returns_empty(self, tmp_file):
        assert load_aliases(tmp_file) == {}

    def test_roundtrip(self, tmp_file):
        save_aliases({"AA:BB:CC:DD:EE:FF": "iPhone"}, tmp_file)
        assert load_aliases(tmp_file) == {"AA:BB:CC:DD:EE:FF": "iPhone"}

    def test_load_invalid_json_returns_empty(self, tmp_file):
        tmp_file.write_text("not json")
        assert load_aliases(tmp_file) == {}

    def test_load_non_dict_returns_empty(self, tmp_file):
        tmp_file.write_text(json.dumps(["not", "a", "dict"]))
        assert load_aliases(tmp_file) == {}

    def test_save_normalizes_mac_case(self, tmp_file):
        save_aliases({"aa:bb:cc:dd:ee:ff": "iPhone"}, tmp_file)
        assert load_aliases(tmp_file) == {"AA:BB:CC:DD:EE:FF": "iPhone"}

    def test_load_normalizes_mac_case(self, tmp_file):
        # Even if file happens to contain lowercase, loading normalizes it.
        tmp_file.write_text(json.dumps({"aa:bb:cc:dd:ee:ff": "iPhone"}))
        assert load_aliases(tmp_file) == {"AA:BB:CC:DD:EE:FF": "iPhone"}


class TestMutators:
    def test_set_adds_entry(self, tmp_file):
        set_alias("aa:bb:cc:dd:ee:ff", "iPhone", tmp_file)
        assert load_aliases(tmp_file) == {"AA:BB:CC:DD:EE:FF": "iPhone"}

    def test_set_overwrites_existing(self, tmp_file):
        set_alias("AA:BB:CC:DD:EE:FF", "iPhone", tmp_file)
        set_alias("AA:BB:CC:DD:EE:FF", "iPad", tmp_file)
        assert load_aliases(tmp_file) == {"AA:BB:CC:DD:EE:FF": "iPad"}

    def test_remove_existing_returns_true(self, tmp_file):
        set_alias("AA:BB:CC:DD:EE:FF", "iPhone", tmp_file)
        assert remove_alias("AA:BB:CC:DD:EE:FF", tmp_file) is True
        assert load_aliases(tmp_file) == {}

    def test_remove_missing_returns_false(self, tmp_file):
        assert remove_alias("AA:BB:CC:DD:EE:FF", tmp_file) is False


class TestResolve:
    def test_returns_name_when_mapped(self):
        aliases = {"AA:BB:CC:DD:EE:FF": "iPhone"}
        assert resolve("aa:bb:cc:dd:ee:ff", aliases) == "iPhone"

    def test_returns_raw_mac_when_unmapped(self):
        aliases = {"AA:BB:CC:DD:EE:FF": "iPhone"}
        assert resolve("11:22:33:44:55:66", aliases) == "11:22:33:44:55:66"

    def test_empty_aliases_returns_raw(self):
        assert resolve("AA:BB:CC:DD:EE:FF", {}) == "AA:BB:CC:DD:EE:FF"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file perms only")
class TestFilePermissions:
    def test_alias_file_is_user_only(self, tmp_path):
        path = tmp_path / "sub" / "aliases.json"
        save_aliases({"AA:BB:CC:DD:EE:FF": "iPhone"}, path)
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"expected 0o600, got {oct(mode)}"

    def test_alias_parent_dir_is_user_only(self, tmp_path):
        path = tmp_path / "sub" / "aliases.json"
        save_aliases({"AA:BB:CC:DD:EE:FF": "iPhone"}, path)
        mode = stat.S_IMODE(path.parent.stat().st_mode)
        assert mode == 0o700, f"expected 0o700, got {oct(mode)}"
