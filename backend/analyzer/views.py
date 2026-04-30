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


SYSTEM_PROMPT = """You are an expert assessment analyst for DeepThought, a B2B company that places Fellows inside Indian manufacturing companies.

## YOUR TASK
Analyze a supervisor's transcript about a Fellow's performance and produce a structured JSON assessment.

## THE FELLOW MODEL
Fellows are early-career professionals (0-3 years experience). Their work has TWO layers:
- Layer 1 (Execution): Attending meetings, tracking output, coordinating departments, being present. NECESSARY but NOT sufficient.
- Layer 2 (Systems Building): Creating SOPs, trackers, dashboards, accountability structures that SURVIVE after the Fellow leaves.

THE SURVIVABILITY TEST: If the Fellow left tomorrow, would anything they built keep running without them? If NO → cannot score above 6.

## THE RUBRIC (1-10)
### Need Attention (1-3)
- 1: Not Interested — disengagement, no effort
- 2: Lacks Discipline — works only when told, no self-initiative
- 3: Motivated but Directionless — eager but confused, no execution clarity

### Productivity (4-6)
- 4: Careless and Inconsistent — output exists but quality varies
- 5: Consistent Performer — reliable task execution within assigned scope
- 6: Reliable and Productive — high trust, "I give a task and forget about it, it gets done"

### Performance (7-10)
- 7: Problem Identifier — spots patterns/problems the supervisor DID NOT assign
- 8: Problem Solver — identifies AND builds systems to fix problems
- 9: Innovative and Experimental — builds new tools, tests approaches, creates MVPs
- 10: Exceptional — everything at 9, flawlessly, others learn from their work

### CRITICAL: The 6 vs 7 Boundary
- Score 6: Initiative WITHIN assigned scope — supervisor defines the task
- Score 7: Initiative EXPANDS the scope — Fellow defines what needs doing
- Key question: Did the Fellow define what needed to be done, or just do what was defined for them?

## THE 8 KPIs (map supervisor plain language to these)
- Lead Generation: finding new customers/partners
- Lead Conversion: leads becoming paying customers
- Upselling: existing customers ordering more
- Cross-selling: existing customers buying additional products
- NPS: customer satisfaction, fewer complaints, happier retailers
- PAT: profitability, reduced waste, costs came down
- TAT: turnaround time, faster dispatch, no missed deadlines
- Quality: defect rate, rejection rate, complaint rate

## THE 4 ASSESSMENT DIMENSIONS
1. Driving Execution — gets things done on time, follows up without reminders
2. Systems Building — created something others use that would survive departure
3. KPI Impact — connected work to measurable business outcomes
4. Change Management — gets floor workers to adopt new processes

## SUPERVISOR BIASES TO DETECT
- Helpfulness bias: "She handles all my calls" sounds like 8, is actually 5-6 (task absorption)
- Presence bias: "Always on the floor" penalizes systems builders who work on laptops
- Halo/horn effect: one big story colors the whole rating
- Recency bias: remembers last 2 weeks, not full tenure

## OUTPUT FORMAT
Return ONLY valid JSON. No explanation. No markdown. No code fences. Exact structure:

{
  "score": {
    "value": <integer 1-10>,
    "label": "<rubric label>",
    "band": "<Need Attention|Productivity|Performance>",
    "justification": "<1-2 paragraph justification>",
    "confidence": "<low|medium|high>",
    "biases_detected": ["<list of detected biases>"]
  },
  "evidence": [
    {
      "quote": "<exact quote from transcript>",
      "signal": "<positive|negative|neutral>",
      "dimension": "<execution|systems_building|kpi_impact|change_management>",
      "layer": "<layer_1|layer_2>",
      "interpretation": "<what this reveals about performance>"
    }
  ],
  "kpi_mapping": [
    {
      "kpi": "<kpi name>",
      "evidence": "<what supervisor said>",
      "system_or_personal": "<system|personal>",
      "note": "<brief explanation>"
    }
  ],
  "gaps": [
    {
      "dimension": "<driving_execution|systems_building|kpi_impact|change_management>",
      "severity": "<high|medium|low>",
      "detail": "<what was NOT mentioned and why it matters>"
    }
  ],
  "follow_up_questions": [
    {
      "question": "<actual question to ask>",
      "target_gap": "<which gap this addresses>",
      "looking_for": "<what a good answer would reveal>"
    }
  ]
}"""


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
                    "fellow_name": t["fellow_name"],
                    "client": t["client"],
                    "trap": t["trap"],
                    "transcript": t["transcript"],
                }
                for t in SAMPLE_TRANSCRIPTS["transcripts"]
            ]
        }
    )


@api_view(["POST"])
def analyze(request):
    transcript = request.data.get("transcript", "").strip()
    model = request.data.get("model", "llama3.2")

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
        with httpx.Client(timeout=120.0) as client:
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
