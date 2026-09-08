"""
Unified AI Service
Provides fault-tolerant AI generation with automatic provider fallback
"""

import os
import json
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import requests

logger = logging.getLogger("ai_service")


# ============================================================================
# AI Provider Interface
# ============================================================================

class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content from the given prompt."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the model being used."""
        pass


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================

class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"[CIRCUIT BREAKER] Circuit opened after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success and potentially close the circuit."""
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("[CIRCUIT BREAKER] Circuit closed after successful request")
    
    def can_attempt(self) -> bool:
        """Check if a request can be attempted."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("[CIRCUIT BREAKER] Circuit moved to HALF_OPEN")
                return True
            return False
        
        return True  # HALF_OPEN


# ============================================================================
# Retry Logic with Exponential Backoff
# ============================================================================

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 32.0):
    """Decorator for retrying with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"[RETRY] Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"[RETRY] All {max_retries} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# AI Result Cache
# ============================================================================

class AIResultCache:
    """Simple in-memory cache for AI results."""
    
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def _generate_key(self, prompt: str, provider: str, model: str) -> str:
        """Generate a cache key."""
        key_data = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, prompt: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired."""
        key = self._generate_key(prompt, provider, model)
        
        if key in self.cache:
            cached = self.cache[key]
            if datetime.now() - cached['timestamp'] < timedelta(seconds=self.ttl):
                logger.info(f"[CACHE] Cache hit for key {key[:16]}...")
                return cached['result']
            else:
                del self.cache[key]
                logger.info(f"[CACHE] Cache expired for key {key[:16]}...")
        
        return None
    
    def set(self, prompt: str, provider: str, model: str, result: Dict[str, Any]):
        """Cache a result."""
        key = self._generate_key(prompt, provider, model)
        self.cache[key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        logger.info(f"[CACHE] Cached result for key {key[:16]}...")
    
    def clear(self):
        """Clear all cached results."""
        self.cache.clear()
        logger.info("[CACHE] Cache cleared")


# ============================================================================
# Gemini Provider
# ============================================================================

class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", timeout: int = 10):
        super().__init__(api_key, model, timeout)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content using Gemini API."""
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get('temperature', 0.7),
                "topK": kwargs.get('top_k', 40),
                "topP": kwargs.get('top_p', 0.95),
                "maxOutputTokens": kwargs.get('max_tokens', 8192),
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'candidates' in data and len(data['candidates']) > 0:
                content = data['candidates'][0]['content']['parts'][0]['text']
                return {
                    'success': True,
                    'content': content,
                    'provider': self.name,
                    'model': self.model,
                    'tokens_used': data.get('usageMetadata', {}).get('totalTokenCount', 0)
                }
            else:
                raise Exception("No content generated")
                
        except requests.exceptions.Timeout:
            raise Exception("Gemini API timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API error: {e}")
        except Exception as e:
            raise Exception(f"Gemini generation failed: {e}")
    
    def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """Get Gemini model information."""
        return {
            'provider': 'Google',
            'model': self.model,
            'api': 'Gemini API'
        }


# ============================================================================
# NVIDIA NIM Provider
# ============================================================================

class NVIDIANIMProvider(AIProvider):
    """NVIDIA NIM API provider."""
    
    def __init__(self, api_key: str, model: str = "meta/llama-3.1-405b-instruct", timeout: int = 10):
        super().__init__(api_key, model, timeout)
        self.base_url = "https://integrate.api.nvidia.com/v1"
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content using NVIDIA NIM API."""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 4096),
            "top_p": kwargs.get('top_p', 0.95)
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                return {
                    'success': True,
                    'content': content,
                    'provider': self.name,
                    'model': self.model,
                    'tokens_used': data.get('usage', {}).get('total_tokens', 0)
                }
            else:
                raise Exception("No content generated")
                
        except requests.exceptions.Timeout:
            raise Exception("NVIDIA NIM API timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"NVIDIA NIM API error: {e}")
        except Exception as e:
            raise Exception(f"NVIDIA NIM generation failed: {e}")
    
    def health_check(self) -> bool:
        """Check if NVIDIA NIM API is accessible."""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """Get NVIDIA model information."""
        return {
            'provider': 'NVIDIA',
            'model': self.model,
            'api': 'NVIDIA NIM API'
        }


# ============================================================================
# OpenRouter Provider
# ============================================================================

class OpenRouterProvider(AIProvider):
    """OpenRouter API provider."""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet", timeout: int = 10):
        super().__init__(api_key, model, timeout)
        self.base_url = "https://openrouter.ai/api/v1"
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content using OpenRouter API."""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("APP_URL", "https://learnflow.app"),
            "X-Title": "LearnFlow"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 4096),
            "top_p": kwargs.get('top_p', 0.95)
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                return {
                    'success': True,
                    'content': content,
                    'provider': self.name,
                    'model': self.model,
                    'tokens_used': data.get('usage', {}).get('total_tokens', 0)
                }
            else:
                raise Exception("No content generated")
                
        except requests.exceptions.Timeout:
            raise Exception("OpenRouter API timeout")
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API error: {e}")
        except Exception as e:
            raise Exception(f"OpenRouter generation failed: {e}")
    
    def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """Get OpenRouter model information."""
        return {
            'provider': 'OpenRouter',
            'model': self.model,
            'api': 'OpenRouter API'
        }


# ============================================================================
# Unified AI Service
# ============================================================================

class UnifiedAIService:
    """Unified AI service with automatic provider fallback."""
    
    def __init__(self):
        self.providers: List[AIProvider] = []
        self.cache = AIResultCache(ttl=3600)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.provider_priority: List[str] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize providers based on environment configuration."""
        # Get provider priority from environment
        priority_str = os.getenv("AI_PROVIDER_PRIORITY", "gemini,nvidia,openrouter")
        self.provider_priority = [p.strip().lower() for p in priority_str.split(",")]
        
        logger.info(f"[AI SERVICE] Provider priority: {self.provider_priority}")
        
        # Initialize providers in priority order
        for provider_name in self.provider_priority:
            try:
                if provider_name == "gemini":
                    api_key = os.getenv("GEMINI_API_KEY")
                    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                    if api_key:
                        provider = GeminiProvider(api_key, model)
                        self.providers.append(provider)
                        self.circuit_breakers[provider_name] = CircuitBreaker()
                        logger.info(f"[AI SERVICE] Initialized Gemini provider with model {model}")
                
                elif provider_name == "nvidia":
                    api_key = os.getenv("NVIDIA_API_KEY")
                    model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-405b-instruct")
                    if api_key:
                        provider = NVIDIANIMProvider(api_key, model)
                        self.providers.append(provider)
                        self.circuit_breakers[provider_name] = CircuitBreaker()
                        logger.info(f"[AI SERVICE] Initialized NVIDIA provider with model {model}")
                
                elif provider_name == "openrouter":
                    api_key = os.getenv("OPENROUTER_API_KEY")
                    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
                    if api_key:
                        provider = OpenRouterProvider(api_key, model)
                        self.providers.append(provider)
                        self.circuit_breakers[provider_name] = CircuitBreaker()
                        logger.info(f"[AI SERVICE] Initialized OpenRouter provider with model {model}")
                
            except Exception as e:
                logger.error(f"[AI SERVICE] Failed to initialize {provider_name} provider: {e}")
        
        if not self.providers:
            logger.error("[AI SERVICE] No AI providers initialized!")
    
    def generate(self, prompt: str, use_cache: bool = True, **kwargs) -> Dict[str, Any]:
        """Generate content with automatic provider fallback."""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            for provider in self.providers:
                cached = self.cache.get(prompt, provider.name, provider.model)
                if cached:
                    cached['cached'] = True
                    cached['processing_time'] = time.time() - start_time
                    return cached
        
        last_error = None
        
        # Try each provider in priority order
        for provider in self.providers:
            provider_name = provider.name.lower()
            
            # Check circuit breaker
            if provider_name in self.circuit_breakers:
                cb = self.circuit_breakers[provider_name]
                if not cb.can_attempt():
                    logger.warning(f"[AI SERVICE] Circuit breaker OPEN for {provider_name}, skipping")
                    continue
            
            try:
                logger.info(f"[AI SERVICE] Attempting generation with {provider_name}")
                
                result = retry_with_backoff(max_retries=2, base_delay=1.0)(provider.generate)(prompt, **kwargs)
                
                # Record success
                if provider_name in self.circuit_breakers:
                    self.circuit_breakers[provider_name].record_success()
                
                # Cache result
                if use_cache and result.get('success'):
                    self.cache.set(prompt, provider.name, provider.model, result)
                
                result['processing_time'] = time.time() - start_time
                result['cached'] = False
                
                logger.info(f"[AI SERVICE] Generation successful with {provider_name} in {result['processing_time']:.2f}s")
                return result
                
            except Exception as e:
                last_error = e
                logger.error(f"[AI SERVICE] {provider_name} failed: {e}")
                
                # Record failure
                if provider_name in self.circuit_breakers:
                    self.circuit_breakers[provider_name].record_failure()
        
        # All providers failed
        logger.error(f"[AI SERVICE] All providers failed. Last error: {last_error}")
        return {
            'success': False,
            'error': str(last_error) if last_error else "All AI providers failed",
            'provider': None,
            'model': None,
            'processing_time': time.time() - start_time
        }
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all providers."""
        health = {}
        for provider in self.providers:
            provider_name = provider.name.lower()
            health[provider_name] = provider.health_check()
        return health
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {}
        for provider in self.providers:
            provider_name = provider.name.lower()
            cb = self.circuit_breakers.get(provider_name)
            status[provider_name] = {
                'model': provider.model,
                'healthy': provider.health_check(),
                'circuit_state': cb.state if cb else 'NO_BREAKER',
                'failure_count': cb.failure_count if cb else 0
            }
        return status


# ============================================================================
# Global AI Service Instance
# ============================================================================

_ai_service: Optional[UnifiedAIService] = None


def get_ai_service() -> UnifiedAIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = UnifiedAIService()
    return _ai_service


def reset_ai_service():
    """Reset the global AI service instance (useful for testing)."""
    global _ai_service
    _ai_service = None
