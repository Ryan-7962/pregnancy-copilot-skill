from scripts.release_check import find_release_blockers


def test_find_release_blockers_reports_private_files_and_ignores_common_local_caches(tmp_path):
    (tmp_path / "docs" / "private").mkdir(parents=True)
    private_log_name = "CONVERSATION" + "_LOG.md"
    (tmp_path / "docs" / "private" / private_log_name).write_text("private", encoding="utf-8")
    (tmp_path / "pregnancy-data").mkdir()
    (tmp_path / "pregnancy-data" / "events.jsonl").write_text("private event", encoding="utf-8")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("venv", encoding="utf-8")
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text("local config", encoding="utf-8")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / "src" / "pkg" / "__pycache__").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__pycache__" / "module.pyc").write_text("bytecode", encoding="utf-8")
    (tmp_path / "real-export.zip").write_text("private zip", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("mac metadata", encoding="utf-8")
    (tmp_path / "._README.md").write_text("appledouble", encoding="utf-8")
    (tmp_path / "README.md").write_text("# ok", encoding="utf-8")

    blockers = find_release_blockers(tmp_path)

    assert "docs/private/" in blockers
    assert f"docs/private/{private_log_name}" not in blockers
    assert "pregnancy-data/" in blockers
    assert not any(blocker.startswith("pregnancy-data/") and blocker != "pregnancy-data/" for blocker in blockers)
    assert ".venv/" not in blockers
    assert ".venv/bin/python" not in blockers
    assert ".codex/" in blockers
    assert ".codex/config.toml" not in blockers
    assert ".pytest_cache/" not in blockers
    assert "src/pkg/__pycache__/" in blockers
    assert "src/pkg/__pycache__/module.pyc" not in blockers
    assert "real-export.zip" in blockers
    assert ".DS_Store" in blockers
    assert "._README.md" in blockers
    assert "README.md" not in blockers


def test_find_release_blockers_reports_private_text_markers(tmp_path):
    private_file_marker = "file" + "_v3_private"
    private_log_marker = "CONVERSATION" + "_LOG"
    private_profile_marker = "pi" + "-rob"
    (tmp_path / "README.md").write_text(f"real export marker: {private_file_marker}", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PUBLIC.md").write_text(private_log_marker, encoding="utf-8")
    (tmp_path / "ops.service").write_text(private_profile_marker, encoding="utf-8")

    blockers = find_release_blockers(tmp_path)

    assert "README.md: contains private marker" in blockers
    assert "docs/PUBLIC.md: contains private marker" in blockers
    assert "ops.service: contains private marker" in blockers


def test_find_release_blockers_reports_local_paths_tokens_and_bot_ids(tmp_path):
    local_path = "/" + "Users" + "/private-user/medical/profile.yaml"
    github_token = "gh" + "p_abcdefghijklmnopqrstuvwxyz123456"
    bot_id = "cli" + "_aa9fbe3273f41cb5"
    (tmp_path / "LOCAL.md").write_text(local_path, encoding="utf-8")
    (tmp_path / "TOKEN.md").write_text(github_token, encoding="utf-8")
    (tmp_path / "BOT.md").write_text(bot_id, encoding="utf-8")

    blockers = find_release_blockers(tmp_path)

    assert "LOCAL.md: contains private pattern" in blockers
    assert "TOKEN.md: contains private pattern" in blockers
    assert "BOT.md: contains private pattern" in blockers
