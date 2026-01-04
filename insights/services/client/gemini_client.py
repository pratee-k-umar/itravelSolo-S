import google.genai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    _client = None
    
    @classmethod
    def get_client(cls):
        """Lazy-load Gemini client instance."""
        
        if cls._client is None:
            try:
                api_key = settings.GEMINI_API_KEY
            
            except AttributeError:
                raise RuntimeError("GEMINI_API_KEY not found in Django settings.")
            
            cls._client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized.")
        
        return cls._client