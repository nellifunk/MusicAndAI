import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from artwork_music.analysis.semantic_base import SemanticProviderError
from artwork_music.analysis.semantic_openai import OpenAISemanticAnalyzer
from artwork_music.analysis.semantic_sidecar import SidecarSemanticAnalyzer
from artwork_music.cli import main, resolve_semantics

PROJECT = Path(__file__).resolve().parents[1]


def analyze_args(output):
    return ["analyze", "--image", str(PROJECT / "examples/demo.png"), "--title", "Example",
            "--artist", "Artist", "--year", "1889", "--art-movement", "Post-Impressionism",
            "--semantic-sidecar", str(PROJECT / "examples/demo.semantic.json"), "--output", str(output)]


def test_cli_end_to_end_repeatable(tmp_path):
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    runs = [tmp_path / "first", tmp_path / "second"]
    for output in runs:
        result = subprocess.run([sys.executable, "main.py", *analyze_args(output)], cwd=PROJECT,
                                text=True, capture_output=True, env=env, timeout=90)
        assert result.returncode == 0, result.stderr
        assert "Romantic" in result.stdout
        assert all((output / p).is_file() for p in ["analysis_raw.json", "composition.json", "grid_overlay.png"])
        assert len(list((output / "midi").glob("*.mid"))) == 17
    first = {str(p.relative_to(runs[0])): p.read_bytes() for p in runs[0].rglob("*") if p.is_file()}
    second = {str(p.relative_to(runs[1])): p.read_bytes() for p in runs[1].rglob("*") if p.is_file()}
    assert first == second
    result = subprocess.run([sys.executable, "main.py", "interact", str(runs[0] / "composition.json")],
        input="set energy 0.2\nset complexity -0.1\nrebuild\nsave my_interpretation\nquit\n",
        cwd=PROJECT, text=True, capture_output=True, env=env, timeout=90)
    assert result.returncode == 0, result.stderr
    saved = runs[0] / "interpretations/my_interpretation/composition.json"
    assert json.loads(saved.read_text())["interpretation"]["delta_movement"] == 0.2


def test_errors_are_clear(tmp_path, capsys):
    args = analyze_args(tmp_path / "output")
    args[args.index("--image") + 1] = str(tmp_path / "missing.png")
    assert main(args) == 2
    assert "Image does not exist" in capsys.readouterr().err
    args = analyze_args(tmp_path / "output")
    args[args.index("--year") + 1] = "0"
    assert main(args) == 2
    assert "Year must" in capsys.readouterr().err
    del args[args.index("--year"):args.index("--year") + 2]
    assert main(args) == 2
    assert "music-era-override" in capsys.readouterr().err


def test_missing_semantics_fails_without_fake_data(tmp_path, rgb, artwork, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    args = SimpleNamespace(semantic_sidecar=None, image=tmp_path / "no_sidecar.png", output=tmp_path,
                           vision_model=None, refresh_semantics=False)
    with pytest.raises(SemanticProviderError, match="semantic-sidecar"):
        resolve_semantics(args, rgb, artwork)
    with pytest.raises(SemanticProviderError, match="Invalid semantic sidecar"):
        SidecarSemanticAnalyzer(tmp_path / "missing.json").analyze(rgb, artwork)


def test_openai_provider_contract_without_network(rgb, artwork, semantics):
    calls = []
    class Responses:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_parsed=semantics)
    client = SimpleNamespace(responses=Responses())
    result = OpenAISemanticAnalyzer("configured-vision-model", client=client).analyze(rgb, artwork)
    assert result == semantics
    request = calls[0]
    images = [item for item in request["input"][1]["content"] if item["type"] == "input_image"]
    assert len(images) == 17
    assert all(image["image_url"].startswith("data:image/png;base64,") for image in images)
    assert request["model"] == "configured-vision-model"
    assert "NOT emotional positivity" in request["input"][0]["content"]


def test_openai_refusal_is_clear(rgb, artwork):
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(output_parsed=None)))
    with pytest.raises(SemanticProviderError, match="semantic-sidecar"):
        OpenAISemanticAnalyzer("configured-model", client=client).analyze(rgb, artwork)


def test_api_semantics_cached_and_reusable_offline(tmp_path, rgb, artwork, semantics, monkeypatch):
    import artwork_music.analysis.semantic_openai as provider
    calls = []
    class Stub:
        def __init__(self, model): pass
        def analyze(self, rgb, artwork):
            calls.append(artwork)
            return semantics
    monkeypatch.setattr(provider, "OpenAISemanticAnalyzer", Stub)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-never-sent")
    args = SimpleNamespace(semantic_sidecar=None, image=tmp_path / "image.png", output=tmp_path,
                           vision_model="test-model", refresh_semantics=False)
    assert resolve_semantics(args, rgb, artwork) == semantics
    monkeypatch.delenv("OPENAI_API_KEY")
    assert resolve_semantics(args, rgb, artwork) == semantics
    assert len(calls) == 1
    changed = rgb.copy()
    changed[0, 0, 0] ^= 1
    with pytest.raises(SemanticProviderError):
        resolve_semantics(args, changed, artwork)
    args.refresh_semantics = True
    with pytest.raises(SemanticProviderError):
        resolve_semantics(args, rgb, artwork)
