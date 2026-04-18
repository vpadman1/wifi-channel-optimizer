import stat
import sys
import pytest

import logging_config


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file perms only")
class TestLoggingFilePermissions:
    def test_log_file_and_dir_are_user_only(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        log_file = config_dir / "wifi-monitor.log"
        monkeypatch.setattr(logging_config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(logging_config, "LOG_FILE", log_file)

        logging_config.configure_logging(verbose=False)
        logging_config.logger.info("touch the file so loguru opens it")

        assert log_file.exists()
        dir_mode = stat.S_IMODE(config_dir.stat().st_mode)
        file_mode = stat.S_IMODE(log_file.stat().st_mode)
        assert dir_mode == 0o700, f"dir expected 0o700, got {oct(dir_mode)}"
        assert file_mode == 0o600, f"file expected 0o600, got {oct(file_mode)}"
