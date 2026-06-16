"""Generate the grounded Decision Brief.

The LLM (Gemini by default) is given the GovernedTools and asked to diagnose the funnel.
It calls the tools to get every number, then writes the executive brief. It cannot run
SQL or compute a statistic — that all happens inside the tools. Swap providers by adding
another `_run_*` function with the same (system, user, tools) -> text contract.
"""
from __future__ import annotations
from dataclasses import dataclass

from .tools import GovernedTools

SYSTEM_PROMPT = """\
You are Helios's Narrator — the analyst who writes the executive Decision Brief for an
e-commerce growth team. You work ONLY from governed tool outputs.

Hard rules (non-negotiable):
- You NEVER invent numbers. Every figure in your brief must come from a tool result.
- You NEVER compute a statistic yourself; the tools already did the math.
- You NEVER guess what a metric means; call get_metric_definition if unsure.
- Use exact metric names (snake_case) when you reference them.

Process:
1. Call list_available_weeks to see the data and the biggest week-over-week move.
2. Call diagnose_conversion_change on that move (you may diagnose another pair too if useful).
3. Optionally call get_metric_definition to ground any term you cite.
4. Write the brief.

Verify-then-trust: every diagnose_conversion_change result carries a `critic` block
(the Critic has already attacked the finding). HONOUR its verdict:
- REFUTE  -> do NOT present the finding as a real growth problem; lead with the Critic's
            reason (e.g. not significant, doesn't reconcile, or a data-quality artifact)
            and recommend fixing data / waiting, not an experiment.
- REVISE  -> present the finding but attach the Critic's caveat verbatim in substance.
- SHIP    -> present with full confidence.
Never contradict the Critic; never quote a dollar figure the Critic refuted.

The decisive distinction is MIX-SHIFT (traffic composition changed) vs RATE-CHANGE
(real in-segment behaviour changed). If the move is mix-dominated, warn against "fixing
the funnel"; if rate-dominated, point to the funnel/UX in the top driver segment.

Output: a crisp Markdown brief an executive can read in 30 seconds, with these sections:
**Headline** (the move + whether it's statistically significant),
**Why it moved** (mix vs rate, with the point contributions),
**Top drivers** (the 1-2 segments that matter, with before->after conversion),
**Dollar impact** (revenue-at-risk),
**Recommended action** (one concrete next step).
Be specific and quantitative; no filler. Do not show your tool calls."""

USER_PROMPT = ("Produce this week's Helios Decision Brief for the Google Merchandise Store "
               "funnel: find the most important week-over-week session-conversion move, "
               "diagnose why it happened, and recommend an action.")

DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass
class BriefResult:
    text: str
    tool_calls: list
    model: str


def generate_decision_brief(df, registry_path, api_key: str,
                            model: str = DEFAULT_MODEL,
                            focus_weeks: tuple | None = None) -> BriefResult:
    """Run the grounded brief with Gemini and return the narrative + the tools it called.

    If focus_weeks=(w0, w1) is given, the brief diagnoses that specific move (so a UI can
    keep the narrative in sync with the weeks on screen); otherwise the model picks the
    biggest week-over-week move itself.
    """
    tools = GovernedTools(df, registry_path)
    user = USER_PROMPT
    if focus_weeks:
        w0, w1 = focus_weeks
        user = (f"Produce the Helios Decision Brief focused on the session-conversion move "
                f"from the week of {w0} to the week of {w1}. Call "
                f"diagnose_conversion_change with week_baseline='{w0}' and "
                f"week_compare='{w1}', then write the brief and recommend an action.")
    text = _run_gemini(SYSTEM_PROMPT, user, tools, api_key, model)
    return BriefResult(text=text, tool_calls=tools.calls, model=model)


def _run_gemini(system: str, user: str, tools: GovernedTools, api_key: str,
                model: str, max_steps: int = 8) -> str:
    """Explicit (manual) Gemini function-calling loop via google-genai: we declare the
    tool schemas, run the model, execute any function calls ourselves, feed results back,
    and repeat until the model returns the final narrative."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:  # noqa: BLE001
        raise SystemExit("google-genai not installed. Run: pip install google-genai") from e

    client = genai.Client(api_key=api_key)
    tool = types.Tool(function_declarations=GovernedTools.DECLARATIONS)
    config = types.GenerateContentConfig(
        system_instruction=system,
        tools=[tool],
        temperature=0.3,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user)])]

    for _ in range(max_steps):
        resp = client.models.generate_content(model=model, contents=contents, config=config)
        cand = resp.candidates[0]
        parts = cand.content.parts or []
        fcalls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if not fcalls:
            return resp.text or ""
        contents.append(cand.content)  # the model's tool-call turn
        for fc in fcalls:
            result = tools.dispatch(fc.name, dict(fc.args or {}))
            contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name=fc.name, response={"result": result})
            ]))
    raise RuntimeError("Reached the tool-call step limit without a final brief.")
