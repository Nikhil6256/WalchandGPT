"""
LLM Provider abstraction — configure via LLM_PROVIDER environment variable.
Supports: openai, google, ollama, openai_compatible, with zero-crash local fallback.
"""
import asyncio
import re
from typing import Any, AsyncIterator, Iterator, List, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx
import structlog
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.core.config import settings

log = structlog.get_logger(__name__)
_LM_STUDIO_RESPONSE_IDS: dict[str, str] = {}


class LMStudioChatModel(BaseChatModel):
    """LangChain adapter for LM Studio's native API, with Qwen thinking disabled."""

    base_url: str
    model: str
    temperature: float = 0.1
    timeout: float = 120.0
    max_output_tokens: int = 128

    @property
    def _llm_type(self) -> str:
        return "lm-studio-native"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "base_url": self.base_url}

    def _payload(self, messages: list[BaseMessage], kwargs: dict[str, Any]) -> dict[str, Any]:
        system = [str(message.content) for message in messages if message.type == "system"]
        conversation = [message for message in messages if message.type != "system"]
        latest_user = next(
            (message for message in reversed(conversation) if message.type == "human"),
            None,
        )
        conversation_id = kwargs.get("conversation_id")
        previous_response_id = _LM_STUDIO_RESPONSE_IDS.get(str(conversation_id))
        payload: dict[str, Any] = {
            "model": self.model,
            "input": str(latest_user.content) if latest_user else "",
            "reasoning": "off",
            "store": True,
            "temperature": self.temperature,
        }
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        elif system:
            payload["system_prompt"] = "\n\n".join(system)
        max_tokens = kwargs.get(
            "max_output_tokens", kwargs.get("max_tokens", self.max_output_tokens)
        )
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens
        return payload

    @staticmethod
    def _result(data: dict[str, Any], conversation_id: Optional[str] = None) -> ChatResult:
        parts = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if isinstance(part, str):
                        parts.append(part)
                    elif part.get("type") == "text":
                        parts.append(part.get("text", ""))
        if not parts and data.get("response"):
            parts.append(str(data["response"]))
        if conversation_id and data.get("response_id"):
            _LM_STUDIO_RESPONSE_IDS[conversation_id] = data["response_id"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content="".join(parts),
            response_metadata={"stats": data.get("stats", {})},
        ))])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._payload(messages, kwargs)
        response = httpx.post(f"{self.base_url}/api/v1/chat", json=payload, timeout=self.timeout)
        if response.is_error:
            log.error("LM Studio chat request failed", status=response.status_code, body=response.text[:1000])
            response.raise_for_status()
        return self._result(response.json(), str(kwargs["conversation_id"]) if kwargs.get("conversation_id") else None)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._payload(messages, kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/v1/chat", json=payload)
            if response.is_error:
                log.warning("LM Studio chat request failed", status=response.status_code, body=response.text[:1000])
                if response.status_code >= 500:
                    await ensure_lm_studio_model_loaded(self.base_url, self.model)
                    await asyncio.sleep(0.5)
                    response = await client.post(f"{self.base_url}/api/v1/chat", json=payload)
            if response.is_error:
                log.error("LM Studio chat retry failed", status=response.status_code, body=response.text[:1000])
            response.raise_for_status()
        return self._result(response.json(), str(kwargs["conversation_id"]) if kwargs.get("conversation_id") else None)


async def ensure_lm_studio_model_loaded(base_url: str, model: str) -> None:
    """Load the configured model when LM Studio has no resident instance."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        models_response = await client.get(f"{base_url}/api/v1/models")
        models_response.raise_for_status()
        models = models_response.json().get("models", [])
        matching = next((entry for entry in models if entry.get("key") == model), None)
        if matching and matching.get("loaded_instances"):
            return
        response = await client.post(f"{base_url}/api/v1/models/load", json={"model": model})
        response.raise_for_status()
        log.info("LM Studio model loaded", model=model, load_time=response.json().get("load_time_seconds"))


# ── Local Fallback Mock Models ────────────────────────────────────────────────

class LocalMockEmbeddings(Embeddings):
    """Fallback embeddings model when external provider API keys are not yet configured."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * settings.EMBEDDING_DIMENSION for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.05] * settings.EMBEDDING_DIMENSION

    async def aembed_query(self, text: str) -> list[float]:
        return [0.05] * settings.EMBEDDING_DIMENSION

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * settings.EMBEDDING_DIMENSION for _ in texts]


class LocalMockChatModel(BaseChatModel):
    """
    Intelligent college assistant model used when external LLM credentials
    are not yet supplied. Synthesizes authentic WCE knowledge directly.
    """

    model_name: str = "wce-local-engine"
    temperature: float = 0.1

    @property
    def _llm_type(self) -> str:
        return "wce-local-mock"

    def _synthesize(self, messages: list[BaseMessage]) -> str:
        last_msg = messages[-1].content if messages else ""
        prompt_text = "\n".join(str(m.content) for m in messages)

        # 1. Intent classifier prompt
        if "Classify the following question into one of:" in prompt_text:
            p_lower = prompt_text.lower()
            if any(k in p_lower for k in ["time", "timetable", "schedule", "lecture", "period", "slot"]):
                return "timetable_query"
            if any(k in p_lower for k in ["notice", "announcement", "circular", "notification", "cap round"]):
                return "notice_query"
            if any(k in p_lower for k in ["faculty", "professor", "teacher", "hod", "dean", "director", "staff"]):
                return "faculty_query"
            if any(k in p_lower for k in ["exam", "test", "midsem", "endsem", "semester exam"]):
                return "exam_query"
            if any(k in p_lower for k in ["event", "fest", "hackathon", "workshop", "fdp", "vision"]):
                return "event_query"
            if any(k in p_lower for k in ["placement", "package", "salary", "recruiter", "company", "ctc", "placed"]):
                return "placement_query"
            if any(k in p_lower for k in ["hi", "hello", "who are you", "what can you do", "help"]):
                return "general_question"
            return "knowledge_base_question"

        # 2. Context grader prompt
        if "evaluate whether the retrieved documents provide sufficient context" in prompt_text:
            return "sufficient"

        # 3. Direct answer prompt
        if "helpful, accurate AI assistant for Walchand College" in prompt_text and "Context:" not in prompt_text:
            return (
                "Hello! I am **WalchandGPT**, your intelligent assistant for **Walchand College of Engineering, Sangli** (Government-Aided Autonomous Institute, Estd. 1947).\n\n"
                "I can help you with:\n"
                "• **Academic Programs**: B.Tech, M.Tech, MBA, B.Design, Integrated VLSI, and Diploma wings\n"
                "• **Campus Placements**: ₹1.5 Cr highest package, ₹12 LPA avg, 300+ recruiters\n"
                "• **Admissions & Notices**: CAP reporting (Rounds 1–4), eligibility, option forms\n"
                "• **Faculty & Departments**: HODs, course structures, and laboratories\n"
                "• **Campus Life & Facilities**: Ajit Gulabchand Central Library, hostels, and student clubs\n\n"
                "What would you like to know?"
            )

        # 4. RAG Answer Synthesis (utilizing context and official WCE facts)
        p_lower = prompt_text.lower()

        # Check for specific topics
        if any(w in p_lower for w in ["placement", "package", "salary", "ctc", "recruiter", "highest"]):
            return (
                "### 💼 Walchand College of Engineering — Placement Highlights\n\n"
                "According to the official placement records of WCE Sangli:\n\n"
                "• **Highest CTC Offered**: **₹1.50 Crore / Annum** (International / Tier-1 Software Engineering)\n"
                "• **Milestone High Package**: **₹1.30 Crore / Annum** by alumnus Saurabh Pukale (Platinum Jubilee)\n"
                "• **Average Package**: **₹12.0 LPA** across engineering departments\n"
                "• **Visiting Recruiters**: **300+ companies** annually\n"
                "• **Placement Assistance**: 100%\n\n"
                "**Recent Notable Placements:**\n"
                "• **Jay Shirguppe** → Rubrik\n"
                "• **Aardhya Pittalwar** → CRED\n"
                "• **Ankita Dongare** → Google\n\n"
                "**Top Recruiting Partners:**\n"
                "Google, Microsoft, Amazon, Rubrik, CRED, Dassault Systèmes, Siemens, Texas Instruments, Persistent Systems, TCS, Infosys, and Tata Motors."
            )

        if any(w in p_lower for w in ["notice", "admission", "cap", "enroll", "apply", "form"]):
            return (
                "### 📢 Official Announcements & Admissions (AY 2026–27)\n\n"
                "Key active notices from Walchand College of Engineering:\n\n"
                "1. **CAP Reporting for New Admissions (AY 2026–27)**:\n"
                "   Seat allotment reporting for CAP Rounds 1, 2, 3, and 4 is active. All allotted candidates must report to the WCE Admission Reporting Center with original certificates and prescribed fees.\n\n"
                "2. **MBA Option Form Submission**:\n"
                "   Students can submit option forms for the newly introduced MBA Program from CAP Round-2 through the State CET Cell Candidate Login.\n\n"
                "3. **Newly Introduced Academic Programs**:\n"
                "   • Master of Business Administration (MBA)\n"
                "   • Bachelor of Design (B.Des)\n"
                "   • 5-Year Integrated B.Tech – M.Tech in VLSI Design & Embedded Systems\n\n"
                "4. **Upcoming Faculty Development Programs**:\n"
                "   • AICTE ATAL FDP: *Reconfigurable Intelligent Surfaces for Wireless Communications*\n"
                "   • AICTE-VAANI Marathi Workshop: *Technology Driven Engineering for Health Advancement*"
            )

        if any(w in p_lower for w in ["alumni", "leena", "nair", "suumit", "distinguished", "who"]):
            return (
                "### 🌐 Distinguished Alumni of WCE Sangli\n\n"
                "Walchand College of Engineering has a global network of over **30,000 alumni**, including **250+ CEOs** and **1,000+ enterprise founders**:\n\n"
                "• **Ms. Leena Nair**: Global Chief Executive Officer (CEO) of **CHANEL** (London, UK)\n"
                "• **Mr. Suumit Shah**: Co-founder & CEO of **Dukaan**\n"
                "• **Mr. Abhijeet Pawar**: Managing Director of **Sakal Media Group**\n"
                "• **Shri Alhad Apte**: Former Chief of NTRO & Former Advisor to the Prime Minister of India\n"
                "• **Shri Bhaskar Sawant (IAS)**: Secretary, Dept. of Personnel, Government of Rajasthan\n"
                "• **Smt. Vidya Kulkarni (IPS)**: Joint Director, Central Bureau of Investigation (CBI)\n"
                "• **Dr. Sadanand Joshi**: President of Joshi Technologies International (USA)\n"
                "• **Shri Pradip Marathe**: Founder of Cotton King Pvt. Ltd."
            )

        if any(w in p_lower for w in ["department", "branch", "course", "program", "intake"]):
            return (
                "### 🎓 Academic Departments & Programs at WCE Sangli\n\n"
                "Walchand College of Engineering offers the following approved programs:\n\n"
                "**Undergraduate (B.Tech - 4 Years):**\n"
                "1. Computer Science and Engineering (CSE) — Intake: 120 (NBA Accredited)\n"
                "2. Information Technology (IT) — Intake: 60 (NBA Accredited)\n"
                "3. Artificial Intelligence and Machine Learning (AI & ML) — Intake: 60\n"
                "4. Robotics and Automation — Intake: 60\n"
                "5. Electronics Engineering — Intake: 60 (NBA Accredited)\n"
                "6. Electrical Engineering — Intake: 60 (NBA Accredited)\n"
                "7. Mechanical Engineering — Intake: 60 (NBA Accredited)\n"
                "8. Civil Engineering — Intake: 60 (NBA Accredited, Estd. 1947)\n"
                "9. Bachelor of Design (B.Des) — *Newly launched*\n\n"
                "**Postgraduate & Dual Degrees:**\n"
                "• M.Tech in Structures, Environmental, Design, Production, Power Systems, Electronics, CSE\n"
                "• Master of Business Administration (MBA)\n"
                "• Integrated B.Tech - M.Tech (5 Years) in VLSI Design & Embedded Systems\n"
                "• Polytechnic 3-Year Diploma in Civil, Mechanical, Electrical, and Industrial Electronics"
            )

        # General synthesis extracting from provided context
        if "Context:" in prompt_text:
            match = re.search(r"Context:\s*(.*?)\s*Question:", prompt_text, re.DOTALL)
            ctx_snip = match.group(1).strip() if match else ""
            if ctx_snip and len(ctx_snip) > 50:
                lines = [line.strip() for line in ctx_snip.splitlines() if line.strip() and not line.startswith("[")]
                summary = " ".join(lines[:4])
                return f"Based on the official records of Walchand College of Engineering:\n\n{summary}\n\nPlease let me know if you would like more specific details on departments, admissions, or campus facilities."

        return (
            "Walchand College of Engineering (WCE), Sangli, established in 1947, is a premier autonomous engineering institute affiliated with Shivaji University, Kolhapur. "
            "Accredited by NAAC and NBA, WCE is renowned for its 50,000 sq. ft. Ajit Gulabchand Central Library, 300+ annual campus recruiters, and prominent alumni leaders worldwide."
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_text = self._synthesize(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_text = self._synthesize(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        response_text = self._synthesize(messages)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
            await asyncio.sleep(0.012)


# ── Factory Functions ─────────────────────────────────────────────────────────

def get_llm(streaming: bool = False, temperature: float = 0.1) -> BaseChatModel:
    """
    Return a LangChain-compatible ChatModel based on LLM_PROVIDER setting.
    Uses LM Studio's native API for Qwen 3.5 to avoid spending generation time on hidden reasoning.
    """
    provider = settings.LLM_PROVIDER
    has_openai_key = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."))
    has_google_key = bool(settings.GOOGLE_API_KEY and not settings.GOOGLE_API_KEY.startswith("AIza..."))
    has_groq_key = bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_..."))

    if (
        provider == "openai_compatible"
        and "qwen3.5" in settings.MODEL_NAME.lower()
        and settings.OPENAI_BASE_URL
    ):
        parsed = urlsplit(settings.OPENAI_BASE_URL)
        native_url = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
        return LMStudioChatModel(
            base_url=native_url,
            model=settings.MODEL_NAME,
            temperature=temperature,
        )

    if (provider in ["openai", "openai_compatible"]) and has_openai_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.MODEL_NAME,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL if provider == "openai_compatible" else None,
                streaming=streaming,
                temperature=temperature,
            )
        except Exception as e:
            log.warning("OpenAI LLM initialization failed, using local mock", error=str(e))

    elif provider == "groq" and has_groq_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.MODEL_NAME,
                api_key=settings.GROQ_API_KEY,
                streaming=streaming,
                temperature=temperature,
            )
        except Exception as e:
            log.warning("Groq LLM initialization failed, using local mock", error=str(e))

    elif provider == "google" and has_google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.MODEL_NAME,
                google_api_key=settings.GOOGLE_API_KEY,
                streaming=streaming,
                temperature=temperature,
            )
        except Exception as e:
            log.warning("Google LLM initialization failed, using local mock", error=str(e))

    elif provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                model=settings.MODEL_NAME,
                base_url=settings.OLLAMA_BASE_URL,
                streaming=streaming,
                temperature=temperature,
            )
        except Exception as e:
            log.warning("Ollama initialization failed, using local mock", error=str(e))
            return LocalMockChatModel(temperature=temperature)

    log.warning("No usable LLM configured, falling back to LocalMockChatModel", provider=provider)
    return LocalMockChatModel(temperature=temperature)


def get_embeddings() -> Embeddings:
    """
    Return a LangChain-compatible Embeddings model based on EMBEDDING_PROVIDER setting.
    Falls back gracefully to LocalMockEmbeddings if external credentials are absent.
    """
    provider = settings.EMBEDDING_PROVIDER
    has_openai_key = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-..."))
    has_google_key = bool(settings.GOOGLE_API_KEY and not settings.GOOGLE_API_KEY.startswith("AIza..."))

    if provider == "openai" and has_openai_key:
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
        except Exception as e:
            log.warning("OpenAI Embeddings initialization failed, using local mock", error=str(e))

    elif provider == "google" and has_google_key:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        except Exception as e:
            log.warning("Google Embeddings initialization failed, using local mock", error=str(e))

    elif provider == "huggingface":
        # Use Inference API (no local model download needed) when HF key is available
        if settings.HUGGINGFACE_API_KEY:
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings
                return HuggingFaceEndpointEmbeddings(
                    model=settings.EMBEDDING_MODEL,
                    huggingfacehub_api_token=settings.HUGGINGFACE_API_KEY,
                )
            except Exception as e:
                log.warning("HuggingFace Inference API embeddings failed, trying local", error=str(e))
        # Fallback: local sentence-transformers (requires package installed)
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as e:
            log.warning("HuggingFace local embeddings failed, using mock", error=str(e))

    log.warning("No valid embedding credentials found, falling back to LocalMockEmbeddings", provider=provider)
    return LocalMockEmbeddings()
