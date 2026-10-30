from scripts.gen_dbt_staging import outputs


def test_generated_staging_matches_conf():
    """Model base_* phải sinh lại từ conf/schema sau mỗi lần sửa conf (uv run python -m scripts.gen_dbt_staging)."""
    stale = [path.name for path, sql in outputs().items() if not path.exists() or path.read_text() != sql]
    assert not stale, f"Chạy lại scripts.gen_dbt_staging: {stale}"
