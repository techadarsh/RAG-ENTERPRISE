"""
LLM client supporting multiple backends: mock, Ollama, Hugging Face
"""
import os
import requests
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Lightweight LLM client supporting three modes:
    - mock: offline placeholder for demos
    - ollama: local inference via Ollama REST API
    - huggingface: cloud inference via Hugging Face Inference API
    
    Mode is determined by environment variables.
    """
    
    def __init__(self):
        """Initialize LLM client by reading environment variables"""
        self.mode = os.getenv("LLM_MODE", "mock").lower()
        self.api_url = os.getenv("MISTRAL_API_URL", "")
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        self.model_name = os.getenv("MISTRAL_MODEL", "mistral")
        
        # Determine backend type from URL
        self.backend = self._detect_backend()
        
        logger.info(f"🤖 LLM Client initialized - Mode: {self.mode}, Backend: {self.backend}")
        if self.api_url:
            logger.info(f"   API URL: {self.api_url}")
    
    def _detect_backend(self) -> str:
        """Detect which backend to use based on mode and URL"""
        if self.mode == "mock":
            return "mock"
        elif "ollama" in self.api_url.lower() or ":11434" in self.api_url:
            return "ollama"
        elif "huggingface" in self.api_url.lower():
            return "huggingface"
        elif self.mode == "api":
            # Generic API mode (original Mistral-style)
            return "mistral"
        return "mock"
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer (backwards compatibility with old interface)
        
        Args:
            query: User query
            context: Retrieved context string
            
        Returns:
            Generated answer
        """
        # Convert context string to list format for generate()
        return self.generate(query, context_text=context)
    
    def generate_answer_with_history(self, query: str, context: str, history: str) -> str:
        """
        Generate answer with conversation history
        
        Args:
            query: Current user query
            context: Retrieved context string
            history: Conversation history string
            
        Returns:
            Generated answer
        """
        # Build enhanced prompt with history
        # context_snippet = context[:500] if len(context) > 500 else context
        context_snippet = context[:3000] # safely include the full retrieved chunk
        full_prompt = f"""You are an enterprise assistant for company policies and documentation. You can ONLY answer questions based on the provided context from the company knowledge base.

IMPORTANT RULES:
1. ONLY answer questions if the information is in the context below
2. IGNORE example data, sample JSON responses, mock data, or placeholder values (like "proj_67890", "user@example.com", etc.) - these are for documentation purposes only
3. If the context only contains API documentation examples or sample code, do NOT treat them as real company information
4. If the question is not related to actual company policies/procedures in the context, respond: "I can only answer questions about company policies, HR information, onboarding, engineering standards, and related documentation. This question is outside my knowledge base."
5. DO NOT make up information or use external knowledge
6. DO NOT answer general questions, coding questions, or topics unrelated to company documentation

Previous conversation:
{history}

Context from Company Knowledge Base:
{context_snippet}

Current question: {query}

Answer (based ONLY on real company information in the context above and conversation history, NOT example data, or decline if not relevant):"""
        
        return self.generate(full_prompt, context_text=context)
    
    def generate(self, prompt: str, context_text: Optional[str] = None) -> str:
        """
        Generate text based on current backend mode
        
        Args:
            prompt: User prompt/query
            context_text: Optional context string to include
            
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
            return self._generate_ollama(full_prompt)
        elif self.backend == "huggingface":
            return self._generate_huggingface(full_prompt)
        elif self.backend == "mistral":
            return self._generate_mistral_api(prompt, context_text or "")
        else:
            logger.warning(f"Unknown backend '{self.backend}', falling back to mock")
            return self._generate_mock(prompt, context_text)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build a structured prompt with context"""
        context_snippet = context[:500] if len(context) > 500 else context
        return f"""You are an enterprise assistant for company policies and documentation. You can ONLY answer questions based on the provided context from the company knowledge base.

IMPORTANT RULES:
1. ONLY answer questions if the information is in the context below
2. IGNORE example data, sample JSON responses, mock data, or placeholder values (like "proj_67890", "user@example.com", etc.) - these are for documentation purposes only
3. If the context only contains API documentation examples or sample code, do NOT treat them as real company information
4. If the question is not related to actual company policies/procedures in the context, respond: "I can only answer questions about company policies, HR information, onboarding, engineering standards, and related documentation. This question is outside my knowledge base."
5. DO NOT make up information or use external knowledge
6. DO NOT answer general questions, coding questions, or topics unrelated to the documentation provided

Context from Company Knowledge Base:
{context_snippet}

User Question: {query}

Answer (based ONLY on real company information in the context above, NOT example data, or decline if not relevant):"""
    
    def _generate_mock(self, prompt: str, context: Optional[str]) -> str:
        """Mock mode - returns placeholder with context snippet"""
        logger.info("📝 Generating mock answer")
        
        if context:
            snippet = (context[:250] + "...") if len(context) > 250 else context
            return f"This is a mock answer for: {prompt}\n\nBased on the retrieved context, I can see information about: {snippet}"
        else:
            return f"This is a mock answer for: {prompt}\n\n(No context provided)"
    
    def _generate_ollama(self, prompt: str) -> str:
        """Generate using local Ollama instance"""
        logger.info(f"🦙 Calling Ollama API ({self.model_name})")
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            answer = data.get("response", "").strip()
            if answer:
                logger.info(f"✅ Ollama response received ({len(answer)} chars)")
                return answer
            else:
                logger.warning("⚠️ Ollama returned empty response")
                return "[Error] Empty response from Ollama"
                
        except requests.exceptions.Timeout:
            logger.error("❌ Ollama request timed out after 120s")
            return "[Error] Ollama request timed out. Try a smaller context or check if Ollama is running."
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to Ollama at {self.api_url}")
            return "[Error] Cannot connect to Ollama. Make sure it's running with 'ollama serve'."
        except Exception as e:
            logger.error(f"❌ Ollama generation failed: {e}")
            return f"[Error] Ollama generation failed: {str(e)}"
    
    def _generate_huggingface(self, prompt: str) -> str:
        """Generate using Hugging Face Inference API"""
        logger.info(f"🤗 Calling Hugging Face Inference API")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                if "generated_text" in data[0]:
                    answer = data[0]["generated_text"].strip()
                    logger.info(f"✅ HuggingFace response received ({len(answer)} chars)")
                    return answer
            elif isinstance(data, dict) and "generated_text" in data:
                answer = data["generated_text"].strip()
                logger.info(f"✅ HuggingFace response received ({len(answer)} chars)")
                return answer
            
            logger.warning(f"⚠️ Unexpected HuggingFace response format: {data}")
            return f"[Warning] Unexpected response format: {str(data)[:200]}"
            
        except requests.exceptions.Timeout:
            logger.error("❌ HuggingFace request timed out")
            return "[Error] HuggingFace request timed out"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("❌ HuggingFace authentication failed - check API key")
                return "[Error] Invalid HuggingFace API key"
            elif e.response.status_code == 503:
                logger.error("❌ HuggingFace model loading (try again in a minute)")
                return "[Error] Model is loading on HuggingFace, please retry in 30-60 seconds"
            else:
                logger.error(f"❌ HuggingFace HTTP error: {e}")
                return f"[Error] HuggingFace API error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"❌ HuggingFace generation failed: {e}")
            return f"[Error] HuggingFace generation failed: {str(e)}"
    
    def _generate_mistral_api(self, query: str, context: str) -> str:
        """Original Mistral API implementation (for backwards compatibility)"""
        logger.info("🌟 Calling Mistral API")
        
        prompt = f"""Answer the user query based on the following context:

Context:
{context}

Query: {query}

Please provide a clear and concise answer based only on the information provided in the context."""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            logger.info("✅ Mistral API response received")
            return answer
        except Exception as e:
            logger.error(f"❌ Mistral API failed: {e}")
            return f"[Error] Mistral API generation failed: {str(e)}"
