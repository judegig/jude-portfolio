import json
from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from llm.providers import get_provider

DEPARTMENTS = {
    "billing": "Billing & Payments",
    "technical": "Technical Support",
    "hr": "Human Resources",
    "facilities": "Facilities",
    "general": "General Affairs",
}

CLASSIFIER_PROMPT = """You are a complaint triage classifier. Given the complaint below, respond with ONLY one of these department codes (no explanation):
billing, technical, hr, facilities, general

Complaint: {complaint}"""


def simulator_page(request):
    return render(request, "simulator/simulator.html", {"departments": DEPARTMENTS})


@require_POST
@csrf_exempt
def simulate(request):
    try:
        body = json.loads(request.body)
        complaint = body.get("complaint", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if not complaint:
        return JsonResponse({"error": "Empty complaint"}, status=400)

    if len(complaint) > 300:
        return JsonResponse({"error": "Too long (max 300 chars)"}, status=400)

    def stage_stream():
        stages = [
            ("intake", "Complaint received", None),
            ("router", "Routing to AI classifier", None),
        ]

        for stage_id, label, dept in stages:
            yield f"data: {json.dumps({'stage': stage_id, 'label': label})}\n\n"

        # Call LLM to classify
        provider = get_provider()
        try:
            raw = provider.chat([
                {"role": "user", "content": CLASSIFIER_PROMPT.format(complaint=complaint)}
            ]).strip().lower()
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'label': str(e)})}\n\n"
            return

        dept_code = raw if raw in DEPARTMENTS else "general"
        dept_name = DEPARTMENTS[dept_code]

        yield f"data: {json.dumps({'stage': 'classifier', 'label': f'AI classified: {dept_name}', 'dept': dept_code})}\n\n"
        yield f"data: {json.dumps({'stage': dept_code, 'label': f'Assigned to {dept_name}', 'dept': dept_code, 'done': True})}\n\n"

    return StreamingHttpResponse(stage_stream(), content_type="text/event-stream")
