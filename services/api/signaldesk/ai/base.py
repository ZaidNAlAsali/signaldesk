from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from ..models import Case
from ..schemas import AnalysisResult


class ProviderError(RuntimeError):
    """Safe provider failure that may be returned to API clients."""


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, case: Case, session: Session) -> AnalysisResult:
        raise NotImplementedError
