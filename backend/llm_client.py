"""
High-performance LLM client with connection pooling, circuit breaker, and adaptive timeouts
Production-grade latency optimizations for on-prem RAG Enterprise
"""
import os
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
    - Support for mock and Ollama backends (on-premises only)
    - Thread-safe class-level shared state
    - Request cancellation support
    """
    
    # Module-level shared HTTP client (connection pool)
    _http_client: Optional[httpx.Client] = None
    _first_call = True  # Track cold start
    _breaker: Optional[CircuitBreaker] = None
    _active_requests: Dict[int, bool] = {}  # Track active requests by thread ID
    
    # Thread-safety locks for shared state
    _lock = threading.Lock()  # Protects _first_call, _http_client, _breaker initialization
    _requests_lock = threading.Lock()  # Protects _active_requests
    
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
        """Detect which backend to use based on mode"""
        if self.mode == "mock":
            return "mock"
        elif self.mode == "api":
            return "ollama"
        return "mock"
    
    def is_available(self) -> bool:
        """Check if LLM is available (circuit breaker state)"""
        if not self.breaker_enabled or LLMClient._breaker is None:
            return True
        return LLMClient._breaker.can_attempt()
    
    def generate_answer(self, query: str, context: str, request=None) -> str:
        """
        Generate answer (backwards compatibility with old interface)
        
        Args:
            query: User query
            context: Retrieved context string
            request: Optional FastAPI Request object for disconnection detection
            
        Returns:
            Generated answer
        """
        return self.generate(query, context_text=context, request=request)
    
    def generate_answer_with_history(self, query: str, context: str, history: str, request=None) -> str:
        """
        Generate answer with conversation history
        
        Args:
            query: Current user query
            context: Retrieved context
            history: Previous conversation (formatted)
            request: Optional FastAPI Request object for disconnection detection
            
        Returns:
            Generated answer
        """
        # Build prompt with history
        full_prompt = f"{history}\n\nContext:\n{context}\n\nUser: {query}\n\nAssistant:"
        return self.generate(full_prompt, request=request)
    
    def generate(self, prompt: str, context_text: Optional[str] = None, request=None) -> str:
        """
        Generate text based on current backend mode with resilience
        
        Args:
            prompt: User prompt/query
            context_text: Optional context string to include
            request: Optional FastAPI Request object for disconnection detection
            
        Returns:
            Generated answer string
        """
        # Build full prompt with context
        if context_text and not ("Context:" in prompt or "context" in prompt.lower()):
            full_prompt = self._build_prompt(prompt, context_text)
        else:
            full_prompt = prompt
        
        # Route to appropriate backend
        if self.backend == "mock":
            return self._generate_mock(prompt, context_text)
        elif self.backend == "ollama":
            return self._generate_ollama_resilient(full_prompt, request=request)
        else:
            logger.warning(f"Unknown backend '{self.backend}', falling back to mock")
            return self._generate_mock(prompt, context_text)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build a structured RAG prompt with strict knowledge base constraints"""
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

Your Response:"""
    
    def _get_timeout(self) -> float:
        """Get adaptive timeout based on cold/warm state (thread-safe)"""
        with LLMClient._lock:
            if LLMClient._first_call:
                return self.initial_timeout_ms / 1000.0
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
    
    def _generate_ollama_resilient(self, prompt: str, request=None) -> str:
        """
        Generate using Ollama with circuit breaker, adaptive timeout, connection pooling
        
        Args:
            prompt: The prompt to send to Ollama
            request: Optional FastAPI Request object for disconnection detection
        """
        # Register this request as active
        thread_id = threading.get_ident()
        with LLMClient._requests_lock:
            LLMClient._active_requests[thread_id] = True
        
        try:
            # Check circuit breaker
            if self.breaker_enabled and LLMClient._breaker:
                if not LLMClient._breaker.can_attempt():
                    logger.warning(f" Circuit breaker OPEN - skipping LLM call")
                    raise Exception("CircuitBreakerOpen")
            
            # Get adaptive timeout
            timeout = self._get_timeout()
            with LLMClient._lock:
                timeout_label = "cold" if LLMClient._first_call else "warm"
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                "stream": False
            }
            
            last_error = None
            start_time = time.perf_counter()
            
            for i, url in enumerate(self.endpoints):
                # Check if request was cancelled before trying next endpoint
                with LLMClient._requests_lock:
                    if thread_id not in LLMClient._active_requests or not LLMClient._active_requests[thread_id]:
                        logger.info(f"Request cancelled - stopping Ollama attempts (tried {i}/{len(self.endpoints)})")
                        raise Exception("RequestCancelled")
                
                try:
                    breaker_state = LLMClient._breaker.state.value if LLMClient._breaker else "N/A"
                    logger.info(f" [Attempt {i+1}/{len(self.endpoints)}] Trying Ollama: {url} (timeout={timeout:.1f}s {timeout_label}, breaker={breaker_state})")
                    
                    response = self._try_generate(url, payload, timeout)
                    
                    if response:
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        logger.info(f" Ollama response received ({len(response)} chars, {latency_ms:.0f}ms) from: {url}")
                        
                        # Record success
                        if self.breaker_enabled and LLMClient._breaker:
                            LLMClient._breaker.record_success()
                        
                        # Mark as warmed up (thread-safe)
                        with LLMClient._lock:
                            LLMClient._first_call = False
                        
                        return response
                    else:
                        logger.warning(f"  Ollama returned empty response from: {url}")
                        
                except Exception as e:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    error_type = type(e).__name__
                    logger.warning(f" Failed at {url} ({latency_ms:.0f}ms): {error_type}: {str(e)[:100]}")
                    last_error = e
                    
                    # Record failure for circuit breaker (only for primary endpoint)
                    if i == 0 and self.breaker_enabled and LLMClient._breaker:
                        LLMClient._breaker.record_failure()
                    
                    continue
            
            # All endpoints failed - user-friendly message
            error_msg = (
                "I'm currently unable to process your request. "
                "Please try again in a moment. If the problem persists, contact support."
            )
            logger.error(f" All Ollama endpoints failed. Last error: {last_error}")
            return error_msg
        finally:
            # Clean up active request tracking
            with LLMClient._requests_lock:
                LLMClient._active_requests.pop(thread_id, None)
    
    def _generate_mock(self, prompt: str, context: Optional[str]) -> str:
        """Mock mode - returns placeholder with context snippet"""
        context_snippet = context[:200] if context else "No context provided"
        return f"[MOCK MODE] This is a simulated response based on: {context_snippet}..."
    
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
