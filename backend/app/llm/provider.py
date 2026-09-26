"""
LLM Provider abstraction — configure via LLM_PROVIDER environment variable.
Supports: openai, google, ollama, openai_compatible.
No application logic should directly import a provider's SDK.
"""
import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.core.config import settings

log = structlog.get_logger(__name__)


def get_llm(streaming: bool = False, temperature: float = 0.1) -> BaseChatModel:
    """
    Return a LangChain-compatible ChatModel based on LLM_PROVIDER setting.
    streaming=True enables token-by-token streaming via LangGraph.
    """
    provider = settings.LLM_PROVIDER

    if provider == "openai" or provider == "openai_compatible":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL if provider == "openai_compatible" else None,
            streaming=streaming,
            temperature=temperature,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            streaming=streaming,
            temperature=temperature,
        )

    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=settings.MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            streaming=streaming,
            temperature=temperature,
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}. "
                         f"Supported: openai, google, ollama, openai_compatible")


def get_embeddings() -> Embeddings:
    """
    Return a LangChain-compatible Embeddings model based on EMBEDDING_PROVIDER setting.
    """
    provider = settings.EMBEDDING_PROVIDER

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    elif provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
        )

    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        return OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    elif provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider!r}. "
                         f"Supported: openai, google, ollama, huggingface")
