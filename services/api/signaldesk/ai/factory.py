from ..config import Settings
from .base import Analyzer, ProviderError
from .demo import DemoAnalyzer
from .openai import OpenAIAnalyzer


def get_analyzer(settings: Settings) -> Analyzer:
    if settings.ai_provider == "demo":
        return DemoAnalyzer()
    if settings.ai_provider == "openai":
        return OpenAIAnalyzer(settings)
    raise ProviderError(f"Unsupported AI provider: {settings.ai_provider}")
