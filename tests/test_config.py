from pathlib import Path

import pytest

from collector.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parent.parent

MINI = """
clustering:
  threshold: 0.35
sources:
  - id: tagesschau
    name: Tagesschau
    media_type: {media_type}
    plus_patterns: {plus}
    feeds:
      - {{url: "https://example.org/a.xml", region: {region}, category: {category}}}
"""


def write(tmp_path, media_type="oeffentlich-rechtlich", region="inland", category="null", plus="[]"):
    p = tmp_path / "sources.yaml"
    p.write_text(MINI.format(media_type=media_type, region=region, category=category, plus=plus), encoding="utf-8")
    return p


def test_loads_example_config():
    cfg = load_config(ROOT / "config" / "sources.yaml")
    assert len(cfg.sources) == 11
    assert cfg.threshold == 0.35
    ids = [s.id for s in cfg.sources]
    assert len(ids) == len(set(ids))


def test_minimal_valid(tmp_path):
    cfg = load_config(write(tmp_path))
    src = cfg.sources[0]
    assert src.feeds[0].region == "inland"
    assert src.feeds[0].category is None


def test_rejects_unknown_media_type(tmp_path):
    with pytest.raises(ConfigError) as e:
        load_config(write(tmp_path, media_type="zeitschrift"))
    assert "tagesschau" in str(e.value)
    assert "media_type" in str(e.value)


def test_rejects_unknown_region_and_category(tmp_path):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, region="europa"))
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, category="politik"))


def test_rejects_duplicate_source_id(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(
        "sources:\n"
        "  - {id: a, name: A, media_type: zeitung, feeds: [{url: 'https://x.org/1'}]}\n"
        "  - {id: a, name: B, media_type: zeitung, feeds: [{url: 'https://x.org/2'}]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(p)


def test_rejects_source_without_feeds(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("sources:\n  - {id: a, name: A, media_type: zeitung, feeds: []}\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_rejects_invalid_plus_pattern(tmp_path):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, plus='["("]'))


def test_yaml_syntax_error_is_configerror(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("sources:\n  - id: a\n   name: [kaputt\n", encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        load_config(p)
    assert "Zeile" in str(e.value)
