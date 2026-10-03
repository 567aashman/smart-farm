"""
SmartFarm - Ask Shyam Agent (Phase 10)
Groq-powered AI assistant with tool calling.

Architecture:
  User Question
      ↓
  Groq (tool selection)
      ↓
  Tool Execution (real farm/weather data)
      ↓
  Tool Result
      ↓
  Groq (final answer)
      ↓
  Farmer Response
"""
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.config import settings
from backend.tools.farm_tools import FarmToolExecutor, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Ask Shyam, a knowledgeable agricultural assistant for SmartFarm.

You help farmers make practical day-to-day farming decisions based on their real farm data, weather conditions, and crop stages.

IMPORTANT RULES:
1. NEVER invent or guess weather data, farm data, crop stages, irrigation values, or market prices.
2. ALWAYS use the available tools to fetch real information before answering farming questions.
3. If a tool returns an error, clearly state that the information is temporarily unavailable.
4. Give practical, actionable advice suited to Indian farming conditions.
5. Be concise and clear. Farmers need simple, direct answers.
6. Always mention the data source (e.g., "Based on your farm data..." or "According to today's weather...").
7. When giving irrigation advice, always explain the reason (rainfall, crop stage, etc.).
8. Never recommend specific pesticides or chemical dosages — refer to local agriculture extension offices for that.
9. Speak respectfully and encouragingly to farmers.
10. VERY IMPORTANT: You must reply in the EXACT SAME LANGUAGE that the user used. For example, if they asked in Hindi, reply entirely in Hindi. If they asked in Marathi, reply in Marathi.

You can help with:
- Should I irrigate today or tomorrow?
- What crops should I grow this season?
- What is my crop's current growth stage?
- What are the weather risks for my farm?
- What should I do today on my farm?
- When should I expect to harvest?
- What are the mandi prices today?

Always fetch the relevant data before answering.
"""


class AskShyamAgent:
    """
    Groq-based AI agent with tool calling for agricultural advice.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if not settings.groq_api_key:
            raise AskShyamError("GROQ_API_KEY is not configured.")
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client

    async def chat(
        self,
        user_message: str,
        farm_id: int,
        user_id: int,
        db: Session,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        weather_service=None,
        market_service=None,
        image_base64: Optional[str] = None,
        language: str = "hi",
    ) -> Dict[str, Any]:
        """
        Process a user message through Groq with tool calling.

        Returns:
            dict with 'reply', 'tools_used', 'sources'
        """
        client = self._get_client()
        executor = FarmToolExecutor(db=db, weather_service=weather_service, market_service=market_service)

        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history (last 10 turns)
        if conversation_history:
            messages.extend(conversation_history[-10:])
            
        # Enforce language
        lang_name = "English" if language == "en" else "Hindi"
        messages.append({"role": "system", "content": f"CRITICAL: The user has selected {lang_name}. You MUST reply entirely in {lang_name}."})



        if image_base64:
            try:
                # Add data URI prefix if missing
                if not image_base64.startswith("data:image"):
                    image_base64 = f"data:image/jpeg;base64,{image_base64}"
                    
                vision_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"The user has uploaded this image of their farm/crop along with the following message: '{user_message}'. Please describe the image in detail and identify any visible issues (diseases, pests, nutrient deficiencies, etc.) so that an agricultural expert system can use your description to provide advice."},
                            {"type": "image_url", "image_url": {"url": image_base64}}
                        ]
                    }
                ]
                logger.info("Analyzing image with qwen/qwen3.8-27b...")
                vision_resp = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=vision_messages,
                    max_tokens=1024,
                )
                image_description = vision_resp.choices[0].message.content
                user_message += f"\n\n[Image Uploaded by User. AI Vision Analysis: {image_description}]"
            except Exception as e:
                logger.error(f"Vision API error: {e}")
                user_message += "\n\n[Image Uploaded by User, but the Vision AI failed to analyze it.]"

        # Inject farm context
        context_msg = f"[Context: The user's farm_id is {farm_id}. Use this for all tool calls.]"
        messages.append({"role": "user", "content": f"{context_msg}\n\n{user_message}"})

        tools_used = []
        sources = []
        max_tool_rounds = 5  # prevent infinite loops

        # ── Agentic Tool-Calling Loop ──
        for round_num in range(max_tool_rounds):
            logger.info(f"Ask Shyam round {round_num + 1}, messages={len(messages)}")

            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=1024,
                temperature=0.3,
            )

            choice = response.choices[0]
            message = choice.message

            # If no more tool calls, we have the final answer
            if not message.tool_calls:
                final_reply = message.content or "I couldn't generate a response. Please try again."
                logger.info(f"Ask Shyam final answer after {round_num + 1} rounds, tools used: {tools_used}")
                return {
                    "reply": final_reply,
                    "tools_used": tools_used,
                    "sources": sources,
                }

            # Add assistant message with tool calls to history
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            # Execute each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"Executing tool: {tool_name}({tool_args})")
                tool_result = await executor.execute(tool_name, tool_args)

                tools_used.append(tool_name)
                sources.append(f"Tool: {tool_name}")

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

        # If we hit the max rounds, get a final answer anyway
        logger.warning("Ask Shyam reached max tool rounds — forcing final response")
        final_resp = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages + [{"role": "user", "content": "Please provide your final answer based on the data gathered."}],
            max_tokens=512,
            temperature=0.3,
        )
        return {
            "reply": final_resp.choices[0].message.content or "Unable to generate response.",
            "tools_used": tools_used,
            "sources": sources,
        }


class AskShyamError(Exception):
    """Raised when Ask Shyam cannot process the request."""
    pass


# Module-level singleton
ask_shyam_agent = AskShyamAgent()
