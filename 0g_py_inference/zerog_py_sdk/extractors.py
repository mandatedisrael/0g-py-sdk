"""
Service extractors for billing information extraction.

This module provides extractors for different service types to extract
input/output counts from requests and responses for billing purposes.

Each service type has different billing models:
- chatbot: Token-based (prompt_tokens + completion_tokens)
- text-to-image: Per-image requested (n parameter)
- image-editing: Per-image requested (n parameter)  
- speech-to-text: Output token-based only

Usage:
    >>> from zerog_py_sdk import create_extractor, ServiceMetadata
    >>> 
    >>> service = broker.get_service(provider_address)
    >>> extractor = create_extractor(service)
    >>> 
    >>> # For chatbot responses
    >>> input_count = extractor.get_input_count(response_content)
    >>> output_count = extractor.get_output_count(response_content)
"""

from abc import ABC, abstractmethod
from typing import Union
import json

from .models import ServiceMetadata


class Extractor(ABC):
    """
    Abstract base class for service extractors.
    
    All extractors must implement:
    - get_svc_info(): Returns the service metadata
    - get_input_count(content): Extracts input count for billing
    - get_output_count(content): Extracts output count for billing
    """
    
    def __init__(self, svc_info: ServiceMetadata):
        """
        Initialize extractor with service metadata.
        
        Args:
            svc_info: Service metadata from the contract
        """
        self._svc_info = svc_info
    
    def get_svc_info(self) -> ServiceMetadata:
        """
        Get the service metadata.
        
        Returns:
            ServiceMetadata object
        """
        return self._svc_info
    
    @abstractmethod
    def get_input_count(self, content: str) -> int:
        """
        Extract input count from request/response content.
        
        Args:
            content: JSON string containing usage information
            
        Returns:
            Input count for billing
        """
        pass
    
    @abstractmethod
    def get_output_count(self, content: str) -> int:
        """
        Extract output count from request/response content.
        
        Args:
            content: JSON string containing usage information
            
        Returns:
            Output count for billing
        """
        pass


class ChatBotExtractor(Extractor):
    """
    Extractor for chatbot/LLM services.
    
    Extracts token counts from OpenAI-compatible usage metadata:
    - Input: usage.prompt_tokens
    - Output: usage.completion_tokens
    
    Example content:
        {"prompt_tokens": 150, "completion_tokens": 300}
    """
    
    def get_input_count(self, content: str) -> int:
        """
        Extract prompt_tokens from usage data.
        
        Args:
            content: JSON string with usage data
            
        Returns:
            Number of prompt tokens
        """
        try:
            if not content:
                return 0
            usage = json.loads(content)
            tokens = usage.get('prompt_tokens', 0)
            return int(tokens) if tokens else 0
        except (json.JSONDecodeError, ValueError, TypeError):
            return 0
    
    def get_output_count(self, content: str) -> int:
        """
        Extract completion_tokens from usage data.
        
        Args:
            content: JSON string with usage data
            
        Returns:
            Number of completion tokens
        """
        try:
            if not content:
                return 0
            usage = json.loads(content)
            tokens = usage.get('completion_tokens', 0)
            return int(tokens) if tokens else 0
        except (json.JSONDecodeError, ValueError, TypeError):
            return 0


class TextToImageExtractor(Extractor):
    """
    Extractor for text-to-image generation services.
    
    Billing is based on the number of images requested (n parameter):
    - Input: n (number of images to generate), defaults to 1
    - Output: Always 0 (billing is input-based only)
    
    Example content (request payload):
        {"prompt": "A beautiful sunset", "n": 4}
    """
    
    def get_input_count(self, content: str) -> int:
        """
        Extract n (image count) from request payload.
        
        Args:
            content: JSON string with request data
            
        Returns:
            Number of images requested (defaults to 1)
        """
        try:
            if not content:
                return 1
            request = json.loads(content)
            n = request.get('n', 1)
            return int(n) if n else 1
        except (json.JSONDecodeError, ValueError, TypeError):
            return 1
    
    def get_output_count(self, content: str) -> int:
        """
        Output count is always 0 for text-to-image.
        
        Billing is based on input (images requested) only.
        """
        return 0


class ImageEditingExtractor(Extractor):
    """
    Extractor for image editing services.
    
    Billing is based on the number of edited images requested (n parameter):
    - Input: n (number of edits to generate), defaults to 1
    - Output: Always 0 (billing is input-based only)
    
    Example content (request payload):
        {"image": "base64...", "prompt": "Make sky purple", "n": 2}
    """
    
    def get_input_count(self, content: str) -> int:
        """
        Extract n (edit count) from request payload.
        
        Args:
            content: JSON string with request data
            
        Returns:
            Number of edits requested (defaults to 1)
        """
        try:
            if not content:
                return 1
            request = json.loads(content)
            n = request.get('n', 1)
            return int(n) if n else 1
        except (json.JSONDecodeError, ValueError, TypeError):
            return 1
    
    def get_output_count(self, content: str) -> int:
        """
        Output count is always 0 for image editing.
        
        Billing is based on input (edits requested) only.
        """
        return 0


class SpeechToTextExtractor(Extractor):
    """
    Extractor for speech-to-text (transcription) services.
    
    Billing is based on output tokens only:
    - Input: Always 0 (audio input not counted)
    - Output: usage.output_tokens
    
    Example content:
        {"output_tokens": 250}
    """
    
    def get_input_count(self, content: str) -> int:
        """
        Input count is always 0 for speech-to-text.
        
        Audio input is handled separately from token counting.
        """
        return 0
    
    def get_output_count(self, content: str) -> int:
        """
        Extract output_tokens from usage data.
        
        Args:
            content: JSON string with usage data
            
        Returns:
            Number of output tokens
        """
        try:
            if not content:
                return 0
            usage = json.loads(content)
            tokens = usage.get('output_tokens', 0)
            return int(tokens) if tokens else 0
        except (json.JSONDecodeError, ValueError, TypeError):
            return 0


def create_extractor(service: ServiceMetadata) -> Extractor:
    """
    Factory function to create the appropriate extractor for a service.
    
    Args:
        service: ServiceMetadata object from the contract
        
    Returns:
        Appropriate Extractor subclass instance
        
    Raises:
        ValueError: If service type is unknown
        
    Example:
        >>> service = broker.get_service(provider_address)
        >>> extractor = create_extractor(service)
        >>> input_count = extractor.get_input_count(usage_json)
    """
    service_type = service.service_type.lower()
    
    if service_type == 'chatbot':
        return ChatBotExtractor(service)
    elif service_type == 'text-to-image':
        return TextToImageExtractor(service)
    elif service_type == 'image-editing':
        return ImageEditingExtractor(service)
    elif service_type == 'speech-to-text':
        return SpeechToTextExtractor(service)
    else:
        raise ValueError(f"Unknown service type: {service.service_type}")


# Mapping of service types to extractor classes
EXTRACTOR_REGISTRY = {
    'chatbot': ChatBotExtractor,
    'text-to-image': TextToImageExtractor,
    'image-editing': ImageEditingExtractor,
    'speech-to-text': SpeechToTextExtractor,
}
