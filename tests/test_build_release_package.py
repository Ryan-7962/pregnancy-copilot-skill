from scripts.build_release_package import build_release_package
from scripts.release_check import find_release_blockers


def test_build_release_package_excludes_private_and_generated_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("# Demo", encoding="utf-8")
    (source / "._README.md").write_text("appledouble", encoding="utf-8")
    (source / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (source / "src" / "pkg").mkdir(parents=True)
    (source / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (source / "src" / "pkg" / "__pycache__").mkdir()
    (source / "src" / "pkg" / "__pycache__" / "module.cpython-311.pyc").write_text("bytecode", encoding="utf-8")
    (source / "build" / "lib").mkdir(parents=True)
    (source / "build" / "lib" / "module.py").write_text("generated", encoding="utf-8")
    (source / "dist").mkdir()
    (source / "dist" / "package.whl").write_text("generated", encoding="utf-8")
    (source / "src" / "demo.egg-info").mkdir()
    (source / "src" / "demo.egg-info" / "PKG-INFO").write_text("generated", encoding="utf-8")
    (source / "docs" / "private").mkdir(parents=True)
    (source / "docs" / "private" / ("CONVERSATION" + "_LOG.md")).write_text("private", encoding="utf-8")
    (source / "docs" / "superpowers").mkdir(parents=True)
    (source / "docs" / "superpowers" / "plan.md").write_text("local plan", encoding="utf-8")
    (source / "docs" / "xiaohongshu").mkdir(parents=True)
    (source / "docs" / "xiaohongshu" / "account-plan.md").write_text(
        "personal promotion plan", encoding="utf-8"
    )
    (source / "docs" / "HOST_CHANNEL_BLACKBOX_TEST_REPORT.md").write_text("local report", encoding="utf-8")
    (source / "private-export-a").mkdir()
    (source / "private-export-a" / "private.md").write_text("private source", encoding="utf-8")
    (source / "private-export-b").mkdir()
    (source / "private-export-b" / "chat.md").write_text("private source", encoding="utf-8")
    (source / ".releaseignore.local").write_text("private-export-a\nprivate-export-b/\n", encoding="utf-8")
    (source / ".venv").mkdir()
    (source / ".codex").mkdir()
    (source / ".codex" / "config.toml").write_text("local config", encoding="utf-8")
    (source / ".env").write_text("secret", encoding="utf-8")
    (source / "xiaohongshu_cookie.txt").write_text("a1=secret", encoding="utf-8")
    (source / "xhs_cookie.txt").write_text("web_session=secret", encoding="utf-8")
    (source / "real.zip").write_text("private zip", encoding="utf-8")
    (source / "local.diff").write_text("diff artifact", encoding="utf-8")

    target = tmp_path / "release"
    copied = build_release_package(source, target)

    assert "README.md" in copied
    assert (target / "README.md").exists()
    assert not (target / "._README.md").exists()
    assert (target / "src" / "pkg" / "__init__.py").exists()
    assert not (target / "src" / "pkg" / "__pycache__").exists()
    assert not (target / "build").exists()
    assert not (target / "dist").exists()
    assert not (target / "src" / "demo.egg-info").exists()
    assert not (target / "docs" / "private").exists()
    assert not (target / "docs" / "superpowers").exists()
    assert not (target / "docs" / "xiaohongshu").exists()
    assert not (target / "docs" / "HOST_CHANNEL_BLACKBOX_TEST_REPORT.md").exists()
    assert not (target / "private-export-a").exists()
    assert not (target / "private-export-b").exists()
    assert not (target / ".releaseignore.local").exists()
    assert not (target / ".venv").exists()
    assert not (target / ".codex").exists()
    assert not (target / ".env").exists()
    assert not (target / "xiaohongshu_cookie.txt").exists()
    assert not (target / "xhs_cookie.txt").exists()
    assert not (target / "real.zip").exists()
    assert not (target / "local.diff").exists()
    assert find_release_blockers(target) == []


def test_build_release_package_keeps_worker_deployment_templates(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("# Demo", encoding="utf-8")
    (source / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (source / "ops").mkdir()
    (source / "ops" / "docker-compose.worker.yml").write_text("services: {}\n", encoding="utf-8")
    (source / "ops" / "pregnancy-copilot.service").write_text("[Unit]\n", encoding="utf-8")
    (source / "ops" / "run-worker-nohup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "DEPLOYMENT_WORKER.md").write_text("# Worker\n", encoding="utf-8")

    target = tmp_path / "release"
    copied = build_release_package(source, target)

    assert "ops/docker-compose.worker.yml" in copied
    assert "ops/pregnancy-copilot.service" in copied
    assert "ops/run-worker-nohup.sh" in copied
    assert "docs/DEPLOYMENT_WORKER.md" in copied
