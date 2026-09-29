from abc import ABC, abstractmethod

import numpy as np

from ..models import Artwork, SemanticAnalysis


class SemanticProviderError(RuntimeError):
    pass


class SemanticAnalyzer(ABC):
    @abstractmethod
    def analyze(self, rgb: np.ndarray, artwork: Artwork) -> SemanticAnalysis:
        """Return validated global semantics and all 16 cells."""
        raise NotImplementedError

