import os

import pytest

from pregnancy_copilot.external_content.credentials import (
    load_xhs_cookie_header,
    normalize_xhs_cookie_input,
    validate_xhs_cookie_header,
    write_xhs_cookie_secret,
)


RAW_COOKIE = "a1=fixture-a1-secret; web_session=fixture-session-secret; webId=fixture-web-id"
NETSCAPE_COOKIE = """# Netscape HTTP Cookie File
.xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\ta1\tfixture-a1-secret
.xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\tweb_session\tfixture-session-secret
.xiaohongshu.com\tTRUE\t/\tTRUE\t2147483647\twebId\tfixture-web-id
"""


def test_normalize_raw_and_netscape_cookie_without_exposing_values():
    assert normalize_xhs_cookie_input(RAW_COOKIE) == RAW_COOKIE
    assert normalize_xhs_cookie_input(NETSCAPE_COOKIE) == RAW_COOKIE

    status = validate_xhs_cookie_header(RAW_COOKIE)
    assert status.valid is True
    assert status.present_names == ("a1", "webId", "web_session")
    assert status.missing_required_names == ()
    assert "fixture" not in repr(status)


def test_validation_reports_names_not_values():
    status = validate_xhs_cookie_header("a1=fixture-a1-secret")

    assert status.valid is False
    assert status.missing_required_names == ("web_session",)
    assert "fixture-a1-secret" not in repr(status)


def test_write_secret_uses_0600_and_requires_explicit_replace(tmp_path, capsys):
    destination = tmp_path / "secrets" / "xiaohongshu_cookie.txt"

    write_xhs_cookie_secret(RAW_COOKIE, destination)

    assert destination.read_text(encoding="utf-8").strip() == RAW_COOKIE
    assert os.stat(destination).st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_xhs_cookie_secret("a1=changed; web_session=changed", destination)
    write_xhs_cookie_secret("a1=changed; web_session=changed", destination, replace=True)
    assert "changed" in destination.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert "fixture-a1-secret" not in captured.out + captured.err
    assert "fixture-session-secret" not in captured.out + captured.err


def test_secret_cannot_be_written_inside_pregnancy_data(tmp_path):
    data_root = tmp_path / "pregnancy-data"
    destination = data_root / "secrets" / "cookie.txt"

    with pytest.raises(ValueError, match="outside pregnancy-data"):
        write_xhs_cookie_secret(RAW_COOKIE, destination, pregnancy_data_root=data_root)


def test_load_cookie_from_environment_path(tmp_path, monkeypatch):
    destination = tmp_path / "xiaohongshu_cookie.txt"
    write_xhs_cookie_secret(RAW_COOKIE, destination)
    monkeypatch.setenv("PREGNANCY_COPILOT_XHS_COOKIE_FILE", str(destination))

    assert load_xhs_cookie_header() == RAW_COOKIE


def test_malformed_cookie_is_rejected_without_value_in_error():
    secret = "this-is-not-a-cookie-secret"

    with pytest.raises(ValueError) as exc_info:
        normalize_xhs_cookie_input(secret)

    assert secret not in str(exc_info.value)


def test_setup_cli_accepts_netscape_cookie_file_without_echo(tmp_path, capsys, monkeypatch):
    from scripts.setup_xiaohongshu_credentials import run_setup

    source = tmp_path / "browser-export.txt"
    source.write_text(NETSCAPE_COOKIE, encoding="utf-8")
    destination = tmp_path / "secret" / "cookie.txt"

    result = run_setup(source, destination, replace=False, pregnancy_data_root=None)

    assert result["valid"] is True
    assert destination.read_text(encoding="utf-8").strip() == RAW_COOKIE
    assert "fixture-a1-secret" not in capsys.readouterr().out
