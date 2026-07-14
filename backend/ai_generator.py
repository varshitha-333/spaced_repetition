"""
AI Generator Module
High-level interface for generating learning materials using the unified AI service
"""

import json
import logging
from typing import Dict, List, Optional
from ai_service import get_ai_service
from ai_prompts import PromptBuilder

logger = logging.getLogger("ai_generator")


class AIGenerator:
    """High-level AI generator for learning materials."""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.prompt_builder = PromptBuilder()
    
    def generate_analysis(self, content: str) -> Dict[str, any]:
        """Generate comprehensive learning material analysis."""
        try:
            prompt = self.prompt_builder.build_analysis_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Analysis generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            # Parse JSON response
            content_text = result['content']
            try:
                # Extract JSON from response
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    analysis = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'analysis': analysis,
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Analysis generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_flashcards(self, content: str) -> Dict[str, any]:
        """Generate high-quality flashcards."""
        try:
            prompt = self.prompt_builder.build_flashcard_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Flashcard generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    flashcards = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'flashcards': flashcards.get('flashcards', []),
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Flashcard generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_quiz(self, content: str) -> Dict[str, any]:
        """Generate exam-quality quiz questions."""
        try:
            prompt = self.prompt_builder.build_quiz_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Quiz generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    quiz = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'questions': quiz.get('questions', []),
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Quiz generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_mindmap(self, content: str) -> Dict[str, any]:
        """Generate structured mindmap."""
        try:
            prompt = self.prompt_builder.build_mindmap_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Mindmap generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    mindmap = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'mindmap': mindmap,
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Mindmap generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_keywords(self, content: str) -> Dict[str, any]:
        """Generate relevant keywords."""
        try:
            prompt = self.prompt_builder.build_keywords_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Keywords generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    keywords = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'keywords': keywords.get('keywords', []),
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Keywords generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_summary(self, content: str) -> Dict[str, any]:
        """Generate comprehensive summary."""
        try:
            prompt = self.prompt_builder.build_summary_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Summary generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    summary = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'summary': summary,
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Summary generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_revision_notes(self, content: str) -> Dict[str, any]:
        """Generate revision notes."""
        try:
            prompt = self.prompt_builder.build_revision_notes_prompt(content)
            result = self.ai_service.generate(prompt, use_cache=True)
            
            if not result.get('success'):
                logger.error(f"[AI GENERATOR] Revision notes generation failed: {result.get('error')}")
                return self._get_error_result(result.get('error'))
            
            content_text = result['content']
            try:
                json_start = content_text.find('{')
                json_end = content_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = content_text[json_start:json_end]
                    revision_notes = json.loads(json_text)
                    
                    return {
                        'success': True,
                        'revision_notes': revision_notes.get('revision_notes', {}),
                        'provider': result['provider'],
                        'model': result['model'],
                        'cached': result.get('cached', False),
                        'processing_time': result.get('processing_time', 0)
                    }
            except json.JSONDecodeError as e:
                logger.error(f"[AI GENERATOR] Failed to parse JSON: {e}")
                return self._get_error_result("Failed to parse AI response")
            
        except Exception as e:
            logger.error(f"[AI GENERATOR] Revision notes generation error: {e}")
            return self._get_error_result(str(e))
    
    def generate_all_artifacts(self, content: str) -> Dict[str, any]:
        """Generate all AI artifacts for the given content."""
        results = {
            'success': True,
            'artifacts': {},
            'errors': []
        }
        
        # Generate each artifact type
        artifacts = [
            ('flashcards', self.generate_flashcards),
            ('quiz', self.generate_quiz),
            ('mindmap', self.generate_mindmap),
            ('keywords', self.generate_keywords),
            ('summary', self.generate_summary),
            ('revision_notes', self.generate_revision_notes)
        ]
        
        for artifact_name, generator_func in artifacts:
            try:
                result = generator_func(content)
                if result.get('success'):
                    results['artifacts'][artifact_name] = result
                else:
                    results['errors'].append(f"{artifact_name}: {result.get('error')}")
                    logger.warning(f"[AI GENERATOR] Failed to generate {artifact_name}")
            except Exception as e:
                results['errors'].append(f"{artifact_name}: {str(e)}")
                logger.error(f"[AI GENERATOR] Error generating {artifact_name}: {e}")
        
        if results['errors']:
            results['success'] = False
        
        return results
    
    def get_service_status(self) -> Dict[str, any]:
        """Get the status of the AI service."""
        return {
            'provider_status': self.ai_service.get_provider_status(),
            'health': self.ai_service.health_check(),
            'cache_size': len(self.ai_service.cache.cache)
        }
    
    def _get_error_result(self, error: str) -> Dict[str, any]:
        """Return a standardized error result."""
        return {
            'success': False,
            'error': error,
            'provider': None,
            'model': None,
            'cached': False,
            'processing_time': 0
        }


# ============================================================================
# Global AI Generator Instance
# ============================================================================

_ai_generator: Optional[AIGenerator] = None


def get_ai_generator() -> AIGenerator:
    """Get the global AI generator instance."""
    global _ai_generator
    if _ai_generator is None:
        _ai_generator = AIGenerator()
    return _ai_generator


def reset_ai_generator():
    """Reset the global AI generator instance (useful for testing)."""
    global _ai_generator
    _ai_generator = None
