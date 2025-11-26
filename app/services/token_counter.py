"""Token Usage Counter for Gemini Models.

This module provides token counting functionality using tiktoken
to track API usage and costs.

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant - Task 4
"""

import tiktoken
from typing import Dict


class TokenCounter:
    """Counts tokens for text inputs and outputs using tiktoken."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize the token counter.

        Args:
            encoding_name: Tiktoken encoding to use.
                          "cl100k_base" is similar to Gemini's tokenization.
        """
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            # Fallback to gpt2 encoding if cl100k_base not available
            print(f"Warning: {encoding_name} not available, using gpt2 encoding")
            self.encoding = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception:
            # Fallback to word-based estimation if encoding fails
            # Rough estimate: 1 token ≈ 0.75 words
            words = len(text.split())
            return int(words / 0.75)

    def count_prompt_tokens(self, prompt: str) -> int:
        """Count tokens in a prompt.

        Args:
            prompt: Prompt text

        Returns:
            Number of tokens in prompt
        """
        return self.count_tokens(prompt)

    def count_response_tokens(self, response: str) -> int:
        """Count tokens in a response.

        Args:
            response: Response text

        Returns:
            Number of tokens in response
        """
        return self.count_tokens(response)

    def count_total_tokens(self, prompt: str, response: str) -> Dict[str, int]:
        """Count tokens for both prompt and response.

        Args:
            prompt: Prompt text
            response: Response text

        Returns:
            Dictionary with prompt_tokens, completion_tokens, and total_tokens
        """
        prompt_tokens = self.count_prompt_tokens(prompt)
        response_tokens = self.count_response_tokens(response)

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
        }


# Global instance for easy access
_token_counter = None


def get_token_counter() -> TokenCounter:
    """Get or create the global token counter instance.

    Returns:
        TokenCounter instance
    """
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter


def count_tokens(text: str) -> int:
    """Convenience function to count tokens in text.

    Args:
        text: Text to count tokens for

    Returns:
        Number of tokens
    """
    counter = get_token_counter()
    return counter.count_tokens(text)
