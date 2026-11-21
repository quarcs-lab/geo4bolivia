"""The build entry point: the order of the builders and the optional after_build step."""

import geo4bolivia.build as build


def _builders(tmp_path, after: bool):
    folder = tmp_path / "builders"
    folder.mkdir()
    text = (
        "CALLS = []\n"
        "def build_geo(): CALLS.append('geo')\n"
        "DATASETS = {'a': lambda: CALLS.append('a'), 'b': lambda: CALLS.append('b')}\n"
    )
    if after:
        text += "def after_build(target): CALLS.append(('after', target))\n"
    (folder / "__init__.py").write_text(text)


def _run(tmp_path, monkeypatch, target):
    monkeypatch.setattr(build.store, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(build, "write_catalog", lambda: build.sys.modules["builders"].CALLS.append("catalog"))
    build.build(target)
    return build.sys.modules["builders"].CALLS


def test_after_build_runs_last_with_the_target(tmp_path, monkeypatch):
    _builders(tmp_path, after=True)
    assert _run(tmp_path, monkeypatch, "all") == ["geo", "a", "b", "catalog", ("after", "all")]


def test_after_build_is_optional(tmp_path, monkeypatch):
    _builders(tmp_path, after=False)
    assert _run(tmp_path, monkeypatch, "b") == ["b", "catalog"]
