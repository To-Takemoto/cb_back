"""
Chat title generation service using LLM for automatic title creation.
"""

from typing import List, Optional
import re
import logging

from src.domain.entity.message_entity import MessageEntity, Role
from src.port.llm_client import LLMClient

logger = logging.getLogger(__name__)


class TitleGenerationService:
    """Service for generating chat titles using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def generate_title(self, messages: List[MessageEntity]) -> Optional[str]:
        """
        Generate a title for a chat based on the conversation messages.
        
        Args:
            messages: List of messages in the conversation
            
        Returns:
            Generated title string, or None if generation fails
        """
        if not messages:
            return None
        
        try:
            # Create title generation prompt based on conversation language
            title_prompt = self._create_title_prompt(messages)
            
            # Use Google Gemini 2.0 Flash for cost-effective title generation
            original_model = getattr(self.llm_client, 'model', None)
            if hasattr(self.llm_client, 'set_model'):
                self.llm_client.set_model("google/gemini-2.0-flash-exp")
            
            try:
                # Make LLM API call for title generation
                response = await self.llm_client.complete_message([title_prompt])
                title = self._extract_and_validate_title(response.get("content", ""))
                return title
            finally:
                # Restore original model if it was changed
                if original_model and hasattr(self.llm_client, 'set_model'):
                    self.llm_client.set_model(original_model)
                    
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            # Fallback to using first user message
            return self._fallback_title(messages)
    
    def _create_title_prompt(self, messages: List[MessageEntity]) -> MessageEntity:
        """
        Create a prompt for title generation based on conversation language.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            MessageEntity containing the title generation prompt
        """
        # Detect primary language of the conversation
        conversation_text = " ".join([msg.content for msg in messages[:3]])  # Use first 3 messages
        is_japanese = self._is_japanese_dominant(conversation_text)
        
        if is_japanese:
            prompt_content = self._create_japanese_prompt(messages)
        else:
            prompt_content = self._create_english_prompt(messages)
        
        return MessageEntity(
            id=0,
            uuid="title-generation",
            role=Role.USER,
            content=prompt_content
        )
    
    def _is_japanese_dominant(self, text: str) -> bool:
        """
        Determine if the text is primarily in Japanese.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if Japanese characters are dominant
        """
        if not text:
            return False
        
        # Count Japanese characters (Hiragana, Katakana, Kanji)
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
        total_chars = len(re.sub(r'\s', '', text))  # Exclude whitespace
        
        if total_chars == 0:
            return False
        
        japanese_ratio = japanese_chars / total_chars
        return japanese_ratio > 0.3  # More than 30% Japanese characters
    
    def _create_japanese_prompt(self, messages: List[MessageEntity]) -> str:
        """Create Japanese title generation prompt."""
        conversation_preview = self._format_conversation_preview(messages, max_length=500)
        
        return f"""以下の会話に基づいて、簡潔で分かりやすいタイトルを生成してください。

会話内容:
{conversation_preview}

要件:
- タイトルは100文字以内
- 会話の内容を的確に表現
- 日本語で生成
- 「タイトル:」などの接頭語は不要
- タイトルのみを出力

タイトル:"""
    
    def _create_english_prompt(self, messages: List[MessageEntity]) -> str:
        """Create English title generation prompt."""
        conversation_preview = self._format_conversation_preview(messages, max_length=500)
        
        return f"""Generate a concise and descriptive title for the following conversation.

Conversation:
{conversation_preview}

Requirements:
- Title must be 100 characters or less
- Accurately represent the conversation content
- Generate in English
- No prefixes like "Title:" needed
- Output only the title

Title:"""
    
    def _format_conversation_preview(self, messages: List[MessageEntity], max_length: int = 500) -> str:
        """
        Format conversation messages for title generation prompt.
        
        Args:
            messages: List of conversation messages
            max_length: Maximum length of the preview
            
        Returns:
            Formatted conversation preview
        """
        preview_parts = []
        current_length = 0
        
        for msg in messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            line = f"{role_label}: {msg.content}"
            
            if current_length + len(line) > max_length:
                if preview_parts:  # If we have at least one message
                    break
                else:  # If first message is too long, truncate it
                    line = line[:max_length-3] + "..."
            
            preview_parts.append(line)
            current_length += len(line) + 1  # +1 for newline
        
        return "\n".join(preview_parts)
    
    def _extract_and_validate_title(self, llm_response: str) -> Optional[str]:
        """
        Extract and validate title from LLM response.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Validated title or None if invalid
        """
        if not llm_response:
            return None
        
        # Clean up the response
        title = llm_response.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "タイトル:", "Title:", "title:", "題名:", "件名:",
            "Subject:", "subject:", "Topic:", "topic:"
        ]
        
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        
        # Remove quotes if present
        if (title.startswith('"') and title.endswith('"')) or \
           (title.startswith("'") and title.endswith("'")):
            title = title[1:-1].strip()
        
        # Validate length
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Ensure title is not empty and meaningful
        if not title or len(title.strip()) < 3:
            return None
        
        return title
    
    def _fallback_title(self, messages: List[MessageEntity]) -> Optional[str]:
        """
        Generate fallback title from first user message.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Fallback title or None
        """
        for msg in messages:
            if msg.role == "user" and msg.content.strip():
                title = msg.content.strip()
                
                # Truncate if too long
                if len(title) > 100:
                    title = title[:97] + "..."
                
                return title
        
        return None