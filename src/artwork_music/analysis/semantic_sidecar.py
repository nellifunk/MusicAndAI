from pathlib import Path

from ..models import SemanticAnalysis
from .semantic_base import SemanticAnalyzer, SemanticProviderError


class SidecarSemanticAnalyzer(SemanticAnalyzer):
    def __init__(self, path: Path):
        self.path = path

    def analyze(self, rgb, artwork) -> SemanticAnalysis:
        try:
            return SemanticAnalysis.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SemanticProviderError(f"Invalid semantic sidecar {self.path}: {exc}") from exc

