"""OpenAI GPT-4o client with streaming support"""
import json
from typing import Dict, List, Optional, AsyncIterator
from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_REASONING_EFFORT,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE,
)
from prompts import SYSTEM_PROMPT, format_user_prompt


class LLMClient:
    """OpenAI GPT-4o client with streaming"""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")

        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self.reasoning_effort = OPENAI_REASONING_EFFORT

    async def get_recommendations(
        self,
        desktop_state: Dict,
        memory_context: Dict,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        Get recommendations from LLM with streaming.

        Args:
            desktop_state: Current desktop state from observer
            memory_context: Context from memory manager
            stream: Whether to stream the response

        Yields:
            Streamed response chunks (if stream=True)

        Returns:
            Complete response (if stream=False)
        """
        # Format the user prompt
        user_prompt = format_user_prompt(
            focused_window=desktop_state.get("focused_window", "unknown"),
            focused_app=desktop_state.get("focused_app", "unknown"),
            timestamp=desktop_state.get("timestamp", ""),
            accessibility_tree=desktop_state.get("accessibility_tree", ""),
            ocr_text=desktop_state.get("ocr_text", ""),
            task_history=memory_context.get("task_history", "No history"),
            preferences=memory_context.get("preferences", "No preferences"),
            goals=memory_context.get("goals", "No goals"),
            history_count=memory_context.get("history_count", 0)
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Build request params
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": OPENAI_MAX_TOKENS,
                "temperature": OPENAI_TEMPERATURE,
                "stream": stream,
                "response_format": {"type": "json_object"}
            }

            # Only add reasoning_effort for o1 models
            if "o1" in self.model:
                request_params["reasoning_effort"] = self.reasoning_effort

            if stream:
                # Stream the response
                response = await self.client.chat.completions.create(**request_params)

                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                # Non-streaming response
                response = await self.client.chat.completions.create(**request_params)

                yield response.choices[0].message.content

        except Exception as e:
            error_response = {
                "error": str(e),
                "predicted_goal": "Error occurred",
                "context_summary": f"Failed to get recommendations: {e}",
                "recommendations": [
                    {
                        "id": 1,
                        "title": "Error - Retry",
                        "description": "An error occurred while processing your request. Please try again.",
                        "impact": "low",
                        "reasoning": "Error recovery",
                        "action": {
                            "type": "none",
                            "target": "",
                            "value": ""
                        }
                    }
                ],
                "workflow_insights": "Please check your API configuration and try again."
            }
            yield json.dumps(error_response)

    async def parse_streamed_response(self, stream: AsyncIterator[str]) -> Dict:
        """
        Collect and parse streamed response into structured data.

        Args:
            stream: AsyncIterator of response chunks

        Returns:
            Parsed JSON response as dict
        """
        full_response = ""
        async for chunk in stream:
            full_response += chunk

        try:
            return json.loads(full_response)
        except json.JSONDecodeError as e:
            print(f"[LLM] Failed to parse response as JSON: {e}")
            print(f"[LLM] Response: {full_response[:500]}...")
            # Return error structure
            return {
                "error": "Failed to parse LLM response",
                "predicted_goal": "Unknown",
                "context_summary": "Parse error occurred",
                "recommendations": [
                    {
                        "id": 1,
                        "title": "Parse Error",
                        "description": "Could not parse LLM response. Please try again.",
                        "impact": "low",
                        "reasoning": "Parse error recovery",
                        "action": {
                            "type": "none",
                            "target": "",
                            "value": ""
                        }
                    }
                ],
                "workflow_insights": f"Parse error: {e}"
            }

    async def get_recommendations_complete(
        self,
        desktop_state: Dict,
        memory_context: Dict
    ) -> Dict:
        """
        Get complete recommendations (convenience method for non-streaming use).

        Args:
            desktop_state: Current desktop state
            memory_context: Memory context

        Returns:
            Parsed recommendations dict
        """
        stream = self.get_recommendations(desktop_state, memory_context, stream=False)
        return await self.parse_streamed_response(stream)
