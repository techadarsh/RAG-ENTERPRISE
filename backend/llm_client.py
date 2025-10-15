"""
High-performance LLM client with connection pooling, circuit breaker, and adaptive timeouts
Production-grade latency optimizations for on-prem RAG Enterprise
"""
import os
import re
import time
import logging
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    import requests
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, skip requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Simple circuit breaker for LLM endpoint"""
    
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 90):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None
        
    def record_success(self):
        """Record successful call"""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            logger.info(" Circuit breaker: HALF_OPEN → CLOSED (recovery successful)")
            self.state = CircuitState.CLOSED
            
    def record_failure(self):
        """Record failed call"""
        self.failures += 1
        if self.failures >= self.failure_threshold and self.state == CircuitState.CLOSED:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            logger.warning(f" Circuit breaker: OPEN (failures={self.failures})")
            
    def can_attempt(self) -> bool:
        """Check if we can attempt a request"""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            # Check if cooldown expired
            if datetime.now() - self.opened_at > timedelta(seconds=self.cooldown_seconds):
                logger.info(" Circuit breaker: OPEN → HALF_OPEN (cooldown expired, testing)")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        # HALF_OPEN: allow one probe request
        return True


class LLMClient:
    """
    High-performance LLM client with:
    - Connection pooling with keep-alive
    - Adaptive timeouts (cold start vs warm)
    - Circuit breaker for fast-fail
    - Structured logging with latency metrics
    - Support for mock, Ollama, HuggingFace backends
    - Thread-safe class-level shared state
    """
    
    # Module-level shared HTTP client (connection pool)
    _http_client: Optional[httpx.Client] = None
    _first_call = True  # Track cold start
    _breaker: Optional[CircuitBreaker] = None
    
    # Thread-safety locks for shared state
    _lock = threading.Lock()  # Protects _first_call, _http_client, _breaker initialization
    
    def __init__(self):
        """Initialize LLM client with environment-based configuration"""
        self.mode = os.getenv("LLM_MODE", "mock").lower()
        self.llm_host = os.getenv("LLM_HOST", "rag-ollama")
        self.llm_port = os.getenv("LLM_PORT", "11434")
        self.model_name = os.getenv("LLM_MODEL", "mistral")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))
        
        # Performance tuning
        self.initial_timeout_ms = int(os.getenv("LLM_INITIAL_TIMEOUT_MS", "20000"))
        self.normal_timeout_ms = int(os.getenv("LLM_TIMEOUT_MS", "5000"))
        self.breaker_enabled = os.getenv("LLM_BREAKER_ENABLED", "true").lower() == "true"
        self.breaker_fails = int(os.getenv("LLM_BREAKER_FAILS", "3"))
        self.breaker_cooldown = int(os.getenv("LLM_BREAKER_COOLDOWN_S", "90"))
        
        # Legacy support
        self.api_url = os.getenv("MISTRAL_API_URL", f"http://{self.llm_host}:{self.llm_port}/api/generate")
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        
        # Build endpoint list
        self.endpoints = self._build_endpoints()
        self.backend = self._detect_backend()
        
        # Initialize shared HTTP client (once per process) - thread-safe
        with LLMClient._lock:
            if LLMClient._http_client is None and HTTPX_AVAILABLE:
                pool_limit = int(os.getenv("HTTPX_POOL_LIMIT", "20"))
                LLMClient._http_client = httpx.Client(
                    limits=httpx.Limits(
                        max_keepalive_connections=pool_limit,
                        max_connections=pool_limit
                    ),
                    headers={"Connection": "keep-alive"},
                    timeout=self.normal_timeout_ms / 1000.0
                )
                logger.info(f" HTTP connection pool initialized (limit={pool_limit})")
            
            # Initialize circuit breaker
            if LLMClient._breaker is None and self.breaker_enabled:
                LLMClient._breaker = CircuitBreaker(
                    failure_threshold=self.breaker_fails,
                    cooldown_seconds=self.breaker_cooldown
                )
                logger.info(f" Circuit breaker initialized (threshold={self.breaker_fails}, cooldown={self.breaker_cooldown}s)")
        
        logger.info(f" LLM Client initialized - Mode: {self.mode}, Backend: {self.backend}")
        logger.info(f"   Primary endpoint: {self.endpoints[0] if self.endpoints else 'None'}")
        logger.info(f"   Model: {self.model_name}, Timeouts: {self.initial_timeout_ms}ms cold / {self.normal_timeout_ms}ms warm")
    
    def _build_endpoints(self) -> List[str]:
        """Build list of endpoints to try (primary + fallbacks)"""
        endpoints = []
        
        # Primary: configured service name (Docker internal network)
        primary = f"http://{self.llm_host}:{self.llm_port}/api/generate"
        endpoints.append(primary)
        
        # Only add host.docker.internal if primary is not localhost
        # (Don't try localhost from inside container - it won't work)
        if "localhost" not in self.llm_host:
            fallback_host = f"http://host.docker.internal:{self.llm_port}/api/generate"
            if fallback_host not in endpoints:
                endpoints.append(fallback_host)
        
        return endpoints
    
    def _detect_backend(self) -> str:
        """Detect which backend to use based on mode and URL"""
        if self.mode == "mock":
            return "mock"
        elif "huggingface" in self.api_url.lower():
            return "huggingface"
        elif self.mode == "api" or "ollama" in self.api_url.lower() or f":{self.llm_port}" in self.api_url:
            return "ollama"
        return "mock"
    
    def is_available(self) -> bool:
        """Check if LLM is available (circuit breaker state)"""
        if not self.breaker_enabled or LLMClient._breaker is None:
            return True
        return LLMClient._breaker.can_attempt()
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer (backwards compatibility with old interface)
        
        Args:
            query: User query
            context: Retrieved context string
            
        Returns:
            Generated answer
        """
        return self.generate(query, context_text=context)
    
    def generate_answer_with_history(self, query: str, context: str, history: str) -> str:
        """
        Generate answer with conversation history
        
        Args:
            query: Current user query
            context: Retrieved context
            history: Previous conversation (formatted)
            
        Returns:
            Generated answer
        """
        # Build prompt with history
        full_prompt = f"{history}\n\nContext:\n{context}\n\nUser: {query}\n\nAssistant:"
        return self.generate(full_prompt, query=query, context_text=context, history=history)
    
    def generate(self, prompt: str, context_text: Optional[str] = None, query: str = "", history: str = "") -> str:
        """
        Generate text based on current backend mode with resilience
        
        Args:
            prompt: User prompt/query
            context_text: Optional context string to include
            query: Original user query (for dynamic timeout calculation)
            history: Conversation history (for dynamic timeout calculation)
            
        Returns:
            Generated answer string
        """
        # Build full prompt with context
        if context_text and not ("Context:" in prompt or "context" in prompt.lower()):
            full_prompt = self._build_prompt(prompt, context_text)
        else:
            full_prompt = prompt
        
        # Use provided context or empty string for timeout calculation
        timeout_context = context_text if context_text else ""
        
        # Fast-path: handle greetings quickly without LLM
        # Use provided query if available, else try to infer from prompt
        user_text = (query or prompt).strip()
        if user_text:
            ql = user_text.lower()
            greetings = {"hi", "hello", "hey", "howdy", "hola", "namaste"}
            if ql in greetings or any(ql.startswith(g + " ") for g in greetings):
                return (
                    "Hi! I can answer questions about your knowledge base. "
                    "Ask me about policies, onboarding, or specific docs."
                )

            # If the user asks an incomplete query like "tell me about"
            if ql.endswith(" about") or ql in {"tell me", "tell me about"}:
                return "What topic should I look up? Please specify the Topic or subject."

        # Route to appropriate backend
        if self.backend == "mock":
            return self._generate_mock(prompt, context_text)
        elif self.backend == "ollama":
            return self._generate_ollama_resilient(full_prompt, query, timeout_context, history)
        elif self.backend == "huggingface":
            return self._generate_huggingface(full_prompt, query, timeout_context, history)
        else:
            logger.warning(f"Unknown backend '{self.backend}', falling back to mock")
            return self._generate_mock(prompt, context_text)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build a structured RAG prompt with strict knowledge base constraints
        """
        return f"""You are an AI assistant for an enterprise knowledge base system. Your role is to help users find information from company documentation.

        CRITICAL RULES - NEVER VIOLATE THESE:
        1. ONLY answer using information from the Context below
        2. If the Context doesn't contain the answer, you MUST say: "I don't have that information in the knowledge base."
        3. NEVER use your general knowledge or training data
        4. NEVER make assumptions or infer information not explicitly in the Context
        5. NEVER provide advice, recommendations, or opinions unless they are explicitly stated in the Context

        ALLOWED BEHAVIORS:
        Answer questions directly from the Context
        Combine information from multiple parts of the Context
        Clarify or rephrase what's in the Context
        Ask for clarification if the question is ambiguous
        Admit when the Context doesn't contain enough information
        Quote relevant sections from the Context when helpful
        Be conversational and helpful in tone

        RESPONSE GUIDELINES:
        - Start with a direct answer when possible
        - Cite which document/section you're referencing but not mention like part 1/15 because user don't understand about chunking
        - If partially answered: provide what you know, then say what's missing
        - For greeting/small-talk: respond briefly, then offer to help with knowledge base questions
        - For questions completely outside the Context: politely decline and redirect to knowledge base topics

        Context Documents:
        {context}

        User Question: {query}

        Your Response:
        """
    
    def _calculate_dynamic_timeout(self, query: str, context: str, history: str = "") -> float:
        """
        Calculate dynamic timeout based on query complexity
        
        Factors considered:
        1. Query length (longer queries = more thinking time)
        2. Context size (more context = more processing)
        3. History size (conversation context)
        4. Question type (reasoning vs simple lookup)
        
        Returns:
            Timeout in seconds
        """
        # Base timeout
        base_timeout = self.normal_timeout_ms / 1000.0
        
        # Factor 1: Query complexity (word count, question marks)
        query_words = len(query.split())
        query_factor = 1.0
        if query_words > 20:
            query_factor = 1.3  # Complex query
        elif query_words > 10:
            query_factor = 1.15  # Medium query
        
        # Questions with "how", "why", "explain" need more time
        reasoning_keywords = ['how', 'why', 'explain', 'compare', 'difference', 'analyze', 'improve']
        if any(keyword in query.lower() for keyword in reasoning_keywords):
            query_factor *= 1.2
        
        # Factor 2: Context size
        context_chars = len(context)
        context_factor = 1.0
        if context_chars > 1500:
            context_factor = 1.3  # Large context
        elif context_chars > 800:
            context_factor = 1.15  # Medium context
        
        # Factor 3: Conversation history
        history_factor = 1.0
        if history and len(history) > 500:
            history_factor = 1.1  # Account for conversation context

        # Calculate final timeout
        dynamic_timeout = base_timeout * query_factor * context_factor * history_factor

        # Clamp to reasonable range (min 6s, max 45s)
        # Lower values keep UI responsive for simple queries
        min_timeout = 6.0
        max_timeout = 45.0
        final_timeout = max(min_timeout, min(dynamic_timeout, max_timeout))

        logger.info(f"🕒 Dynamic timeout: {final_timeout:.1f}s (query={query_factor:.2f}x, context={context_factor:.2f}x, history={history_factor:.2f}x)")

        return final_timeout
    
    def _get_timeout(self, query: str = "", context: str = "", history: str = "") -> float:
        """
        Get adaptive timeout based on:
        1. Cold/warm state
        2. Query complexity (if dynamic timeout enabled)
        """
        # Check if dynamic timeout is enabled
        dynamic_enabled = os.getenv("LLM_DYNAMIC_TIMEOUT", "true").lower() == "true"
        
        # Cold start always uses initial timeout
        with LLMClient._lock:
            if LLMClient._first_call:
                logger.info(f" Using cold start timeout: {self.initial_timeout_ms / 1000.0:.1f}s")
                return self.initial_timeout_ms / 1000.0
        
        # Warm calls: use dynamic timeout if enabled and inputs provided
        if dynamic_enabled and query and context:
            return self._calculate_dynamic_timeout(query, context, history)
        
        # Fallback to normal timeout
        return self.normal_timeout_ms / 1000.0
    
    def _try_generate(self, url: str, payload: dict, timeout: float) -> str:
        """Attempt generation with a single endpoint"""
        if HTTPX_AVAILABLE and LLMClient._http_client:
            # Use shared connection pool
            r = LLMClient._http_client.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        else:
            import requests
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        
        # Handle different response formats
        response_text = (
            data.get("response") or 
            data.get("text") or 
            data.get("generated_text") or 
            ""
        ).strip()
        
        return response_text

    def _postprocess_answer(self, text: str) -> str:
        """Clean up known artifacts like '(Part N/M)' and normalize spaces."""
        if not text:
            return text
        # Remove patterns like '(Part 1/10)' or 'Part 1/10'
        patterns = [
            r"\(\s*Part\s+\d+\s*/\s*\d+\s*\)",
            r"\bPart\s+\d+\s*/\s*\d+\b",
        ]
        for pat in patterns:
            text = re.sub(pat, "", text, flags=re.IGNORECASE)
        # Collapse multiple spaces and tidy punctuation spacing
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text
    
    def _generate_ollama_resilient(self, prompt: str, query: str = "", context: str = "", history: str = "") -> str:
        """
        Generate text using Ollama with circuit breaker and retry logic
        
        Args:
            prompt: Full prompt to send to LLM
            query: Original user query (for dynamic timeout)
            context: Retrieved context (for dynamic timeout)
            history: Conversation history (for dynamic timeout)
            
        Returns:
            Generated text
        """
        # Fast-fail if circuit breaker is open and cooldown not expired
        if self.breaker_enabled and LLMClient._breaker and not LLMClient._breaker.can_attempt():
            logger.warning(" LLM circuit open - skipping request")
            return "LLM temporarily unavailable. Please try again shortly."

        # Determine timeout (cold vs dynamic)
        timeout = self._get_timeout(query, context, history)

        # Decide a conservative generation length for non-streaming
        # Large num_predict blocks until completion; cap for responsiveness
        default_cap = int(os.getenv("LLM_MAX_TOKENS_NONSTREAM", "200"))
        # If the query is very short or empty, keep it smaller but still adequate
        short_query_cap = int(os.getenv("LLM_MAX_TOKENS_SHORT_QUERY", "128"))
        effective_num_predict = min(self.max_tokens, default_cap)
        if not query or len(query.split()) < 4:
            effective_num_predict = min(effective_num_predict, short_query_cap)

        # Build payload for Ollama /api/generate
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "options": {
                # Keep options modest for latency; can be tuned via env if mapped later
                "temperature": self.temperature,
                "num_predict": effective_num_predict,
                # No explicit stop tokens to avoid premature truncation
            },
            "stream": False,
        }

        last_error: Optional[Exception] = None
        attempts = 0

        # Try each endpoint with a small retry budget per endpoint
        for endpoint_idx, url in enumerate(self.endpoints):
            per_endpoint_retries = int(os.getenv("LLM_RETRIES_PER_ENDPOINT", "1"))
            for retry in range(per_endpoint_retries + 1):
                attempts += 1
                try:
                    logger.info(
                        f" Generating via Ollama (endpoint {endpoint_idx+1}/{len(self.endpoints)} attempt {retry+1}, timeout {timeout:.1f}s, num_predict {effective_num_predict})"
                    )
                    start = time.perf_counter()
                    response_text = self._try_generate(url, payload, timeout)
                    latency_ms = (time.perf_counter() - start) * 1000

                    # Success: reset breaker and clear cold-start flag
                    if self.breaker_enabled and LLMClient._breaker:
                        LLMClient._breaker.record_success()
                    with LLMClient._lock:
                        LLMClient._first_call = False

                    logger.info(
                        f" Ollama success in {latency_ms:.0f}ms via {url} (attempt {attempts})"
                    )

                    if response_text:
                        return self._postprocess_answer(response_text)
                    else:
                        # Treat empty response as error to try fallback
                        raise ValueError("Empty response from LLM")

                except Exception as e:
                    last_error = e
                    # Record failure for breaker after all fallbacks? Opt to record per-failure to trip quickly.
                    if self.breaker_enabled and LLMClient._breaker:
                        LLMClient._breaker.record_failure()
                    # Brief backoff only on retry within same endpoint
                    if retry < per_endpoint_retries:
                        backoff_ms = int(os.getenv("LLM_RETRY_BACKOFF_MS", "250"))
                        time.sleep(backoff_ms / 1000.0)
                    logger.warning(
                        f" Ollama attempt failed via {url} (retry {retry}/{per_endpoint_retries}, endpoint {endpoint_idx+1}/{len(self.endpoints)}): {type(e).__name__}: {str(e)[:140]}"
                    )
            # Move to next endpoint if any

        # If we reach here, all attempts failed
        msg = (
            f"Error generating response after {attempts} attempt(s). "
            f"Last error: {type(last_error).__name__ if last_error else 'Unknown'}: {str(last_error)[:200] if last_error else ''}"
        )
        logger.error(msg)
        return msg
    
    def _generate_mock(self, prompt: str, context: Optional[str]) -> str:
        """Mock mode - returns placeholder with context snippet"""
        context_snippet = context[:200] if context else "No context provided"
        return f"[MOCK MODE] This is a simulated response based on: {context_snippet}..."
    
    def _generate_huggingface(self, prompt: str, query: str = "", context: str = "", history: str = "") -> str:
        """
        Generate using Hugging Face Inference API
        
        Args:
            prompt: Full prompt to send to LLM
            query: Original user query (for dynamic timeout)
            context: Retrieved context (for dynamic timeout)
            history: Conversation history (for dynamic timeout)
            
        Returns:
            Generated text
        """
        logger.info(f" Generating answer via HuggingFace")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": self.temperature,
                "max_new_tokens": self.max_tokens,
            }
        }
        
        try:
            timeout = self._get_timeout(query, context, history)
            if HTTPX_AVAILABLE and LLMClient._http_client:
                r = LLMClient._http_client.post(self.api_url, json=payload, headers=headers, timeout=timeout)
                r.raise_for_status()
                data = r.json()
            else:
                import requests
                r = requests.post(self.api_url, json=payload, headers=headers, timeout=timeout)
                r.raise_for_status()
                data = r.json()
            
            response_text = data[0].get("generated_text", "").strip()
            with LLMClient._lock:
                LLMClient._first_call = False
            return self._postprocess_answer(response_text)
            
        except Exception as e:
            logger.error(f"HuggingFace generation failed: {type(e).__name__}: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    @classmethod
    def warmup(cls, test_prompt: str = "ping") -> bool:
        """
        Warm up the LLM model (call once on startup)
        Returns True if successful, False otherwise
        """
        try:
            logger.info(" Warming up LLM model...")
            client = cls()
            
            if client.backend == "ollama":
                payload = {
                    "model": client.model_name,
                    "prompt": test_prompt,
                    "options": {"num_predict": 5},
                    "stream": False
                }
                
                url = client.endpoints[0]
                timeout = client.initial_timeout_ms / 1000.0
                
                start = time.perf_counter()
                response = client._try_generate(url, payload, timeout)
                latency_ms = (time.perf_counter() - start) * 1000
                
                if response:
                    logger.info(f" LLM warmed up successfully ({latency_ms:.0f}ms)")
                    with cls._lock:
                        cls._first_call = False
                    return True
                    
        except Exception as e:
            logger.warning(f"  LLM warmup failed (non-fatal): {type(e).__name__}: {str(e)[:100]}")
        
        return False
    
    @classmethod
    def keepalive_probe(cls) -> bool:
        """
        Send a lightweight keep-alive request to prevent model eviction
        Returns True if successful, False otherwise
        """
        try:
            client = cls()
            
            if client.backend == "ollama" and HTTPX_AVAILABLE and cls._http_client:
                # Just check /api/tags (lightweight)
                url = f"http://{client.llm_host}:{client.llm_port}/api/tags"
                r = cls._http_client.get(url, timeout=2.0)
                return r.status_code == 200
                
        except Exception:
            pass
        
        return False
    
    @classmethod
    def close(cls):
        """Close shared HTTP client (call on shutdown)"""
        if cls._http_client:
            cls._http_client.close()
            logger.info(" HTTP connection pool closed")
