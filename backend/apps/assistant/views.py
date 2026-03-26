"""SSE chat endpoint for the AI assistant."""

import json
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.core.auth import get_user_from_token

from .tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Cora, a helpful assistant for contract management.
You help users find information about their customers, contracts, invoices, and products.
Answer in the same language the user writes in.
Be concise and use tables or lists when presenting multiple items.
When you don't have enough information, ask clarifying questions.
Do not make up data — only use information returned by your tools."""

RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(user_id: int) -> bool:
    """Return True if rate limit exceeded."""
    key = f"assistant_rate:{user_id}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT_MAX:
        return True
    cache.set(key, count + 1, RATE_LIMIT_WINDOW)
    return False


@method_decorator(csrf_exempt, name="dispatch")
class ChatView(View):
    def _get_user(self, request):
        """Resolve user from Bearer token or admin_token cookie."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = get_user_from_token(token)
            if user:
                return user

        # Fallback: read JWT from cookies
        for cookie_name in ("admin_token", "auth_token"):
            token = request.COOKIES.get(cookie_name)
            if token:
                user = get_user_from_token(token)
                if user:
                    return user

        return None

    def post(self, request):
        user = self._get_user(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=403)

        tenant = getattr(user, "tenant", None)
        if not tenant:
            return JsonResponse({"error": "No active tenant"}, status=403)

        if _check_rate_limit(user.id):
            return JsonResponse(
                {"error": "Rate limit exceeded. Please wait before sending more messages."},
                status=429,
            )

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message = body.get("message", "").strip()
        history = body.get("history", [])

        if not message:
            return JsonResponse({"error": "Message is required"}, status=400)

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            return JsonResponse({"error": "AI assistant not configured"}, status=503)

        response = StreamingHttpResponse(
            self._stream_response(tenant, user, message, history, api_key),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _stream_response(self, tenant, user, message, history, api_key):
        """Generator that yields SSE events."""
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Build messages from history + new message
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        try:
            # Agentic loop: keep calling Claude until we get a text response
            max_iterations = 10
            for _ in range(max_iterations):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )

                # Process response content blocks
                text_parts = []
                tool_uses = []

                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_uses.append(block)

                # If there are tool calls, execute them and continue the loop
                if tool_uses:
                    # Add assistant message with all content blocks
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute each tool and add results
                    tool_results = []
                    for tool_use in tool_uses:
                        result = execute_tool(tenant, tool_use.name, tool_use.input, user=user)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                        })

                    messages.append({"role": "user", "content": tool_results})

                    # If there was also text, stream it
                    if text_parts:
                        for part in text_parts:
                            yield f"data: {json.dumps({'text': part})}\n\n"
                    continue

                # No tool calls — stream the final text response
                full_text = "".join(text_parts)
                if full_text:
                    # Send in chunks for streaming feel
                    chunk_size = 50
                    for i in range(0, len(full_text), chunk_size):
                        chunk = full_text[i:i + chunk_size]
                        yield f"data: {json.dumps({'text': chunk})}\n\n"
                break

        except Exception as e:
            logger.exception("Assistant chat error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"
