import json
from pathlib import Path
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from llm.providers import get_provider

SYSTEM_PROMPT_PATH = Path(__file__).parent / "you.md"
MAX_HISTORY = 10


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def agent_page(request):
    if "agent_history" not in request.session:
        request.session["agent_history"] = []
    return render(request, "agent/agent.html")


@require_POST
@csrf_exempt
def agent_chat(request):
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    if len(user_message) > 500:
        return JsonResponse({"error": "Message too long (max 500 chars)"}, status=400)

    history = request.session.get("agent_history", [])
    history.append({"role": "user", "content": user_message})
    history = history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": _load_system_prompt()}] + history

    def token_stream():
        provider = get_provider()
        full_response = []
        try:
            for token in provider.chat_stream(messages):
                full_response.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        assistant_reply = "".join(full_response)
        history.append({"role": "assistant", "content": assistant_reply})
        request.session["agent_history"] = history[-MAX_HISTORY:]
        request.session.modified = True
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingHttpResponse(token_stream(), content_type="text/event-stream")


@require_GET
def agent_clear(request):
    request.session["agent_history"] = []
    return JsonResponse({"ok": True})
