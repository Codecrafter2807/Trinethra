import json
import re
import httpx
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

OLLAMA_URL = "http://localhost:11434"

# Load data files once at startup
DATA_DIR = Path(settings.DATA_DIR)

with open(DATA_DIR / "rubric.json") as f:
    RUBRIC = json.load(f)

with open(DATA_DIR / "sample-transcripts.json") as f:
    SAMPLE_TRANSCRIPTS = json.load(f)


SYSTEM_PROMPT = f"""You are an expert assessment analyst for DeepThought.

## YOUR TASK
Analyze a supervisor's transcript about a Fellow's performance and produce a structured JSON assessment based on the provided rubric.

## THE RUBRIC
Name: {RUBRIC['rubric']['name']}
Scale: {RUBRIC['rubric']['scale']}
Critical Boundary: {RUBRIC['rubric']['criticalBoundary']['description']}

Bands and Levels:
{json.dumps(RUBRIC['rubric']['bands'], indent=2)}

## ASSESSMENT DIMENSIONS
{json.dumps(RUBRIC['assessmentDimensions'], indent=2)}

## BUSINESS KPIs
{json.dumps(RUBRIC['kpis'], indent=2)}

## ANALYTICAL FRAMEWORK
1. Layer 1 (Execution): Task-level work, being present, following orders.
2. Layer 2 (Systems Building): Creating tools/SOPs that survive departure.
3. THE SURVIVABILITY TEST: If the Fellow left tomorrow, would the system keep running? If NO -> score cannot exceed 6.
4. DETECT BIASES: Helpfulness bias, Presence bias, Halo/Horn effect, Recency bias.

## OUTPUT FORMAT
Return ONLY valid JSON. Exact structure:
{{
  "score": {{
    "value": <int>, "label": "<string>", "band": "<string>",
    "justification": "<1-2 paragraphs>", "confidence": "<low|medium|high>",
    "biases_detected": ["<list>"]
  }},
  "evidence": [
    {{
      "quote": "<string>", "signal": "<pos|neg|neu>",
      "dimension": "<execution|systems_building|kpi_impact|change_management>",
      "layer": "<layer_1|layer_2>", "interpretation": "<string>"
    }}
  ],
  "kpi_mapping": [
    {{ "kpi": "<string>", "evidence": "<string>", "system_or_personal": "<system|personal>", "note": "<string>" }}
  ],
  "gaps": [
    {{ "dimension": "<string>", "severity": "<high|med|low>", "detail": "<string>" }}
  ],
  "follow_up_questions": [
    {{ "question": "<string>", "target_gap": "<string>", "looking_for": "<string>" }}
  ]
}}"""


def extract_json(raw: str) -> dict:
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON. Raw: {raw[:500]}")


@api_view(["GET"])
def health(request):
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            models = resp.json().get("models", [])
            return Response(
                {"ollama": "connected", "available_models": [m["name"] for m in models]}
            )
    except Exception as e:
        return Response(
            {
                "ollama": "unreachable",
                "error": str(e),
                "hint": f"Run 'ollama serve' or check that Ollama is running",
            }
        )


@api_view(["GET"])
def samples(request):
    return Response(
        {
            "transcripts": [
                {
                    "id": t["id"],
                    "fellow_name": t["fellow"]["name"],
                    "client": t["company"]["name"],
                    "trap": t.get("scoringNotes", ""),
                    "transcript": t["transcript"],
                }
                for t in SAMPLE_TRANSCRIPTS["transcripts"]
            ]
        }
    )


@api_view(["POST"])
def analyze(request):
    transcript = request.data.get("transcript", "").strip()
    model = request.data.get("model", "llama3.2:latest")

    if not transcript:
        return Response(
            {"error": "Transcript cannot be empty."}, status=status.HTTP_400_BAD_REQUEST
        )

    user_prompt = f"""Analyze this supervisor transcript and return a JSON assessment.

TRANSCRIPT:
{transcript}

Remember:
- Map supervisor language to KPIs (they never use KPI terms)
- Distinguish Layer 1 (task execution) from Layer 2 (systems building)
- Apply the Survivability Test before scoring above 6
- Flag supervisor biases explicitly
- Check all 4 assessment dimensions for gaps
- Return ONLY valid JSON, nothing else."""

    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 3000},
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        return Response(
            {
                "error": f"Cannot connect to Ollama at {OLLAMA_URL}. Make sure Ollama is running."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except httpx.TimeoutException:
        return Response(
            {"error": "Ollama timed out. Try a smaller model like phi3."},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    raw_output = data.get("response", "")

    try:
        analysis = extract_json(raw_output)
    except ValueError:
        return Response(
            {
                "error": "Model output was not valid JSON. Try again.",
                "raw_output": raw_output[:1000],
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return Response({"analysis": analysis, "model_used": model})
