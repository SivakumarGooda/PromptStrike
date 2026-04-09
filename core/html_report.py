from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, List


def _load_jsonl(jsonl_path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    if not jsonl_path.exists():
        return items

    for raw_line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return items


def _safe_json(data: Any) -> str:
    return html.escape(json.dumps(data, ensure_ascii=False, indent=2))


def _collect_summary(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    verdicts = {
        "success": 0,
        "suspicious": 0,
        "failed": 0,
    }
    keyword_counts: Dict[str, int] = {}

    for case in cases:
        verdict = str(case.get("final_verdict", "failed"))
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

        for turn in case.get("turns", []):
            evaluation = turn.get("evaluation", {})
            for match in evaluation.get("indicator_matches", []):
                keyword_counts[match] = keyword_counts.get(match, 0) + 1

    keyword_counts = dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True))

    return {
        "total_cases": len(cases),
        "verdicts": verdicts,
        "keyword_counts": keyword_counts,
    }


def _render_summary(summary: Dict[str, Any]) -> str:
    verdicts = summary.get("verdicts", {})
    keyword_counts = summary.get("keyword_counts", {})

    keyword_rows = ""
    for key, value in keyword_counts.items():
        keyword_rows += (
            f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
        )

    keyword_table = (
        f"""
        <h2>Keyword Counts</h2>
        <table>
          <tr><th>Keyword</th><th>Count</th></tr>
          {keyword_rows}
        </table>
        """
        if keyword_rows
        else "<h2>Keyword Counts</h2><p>No keyword matches found.</p>"
    )

    return f"""
    <div class="card">
      <h2>Summary</h2>
      <p><strong>Total Cases:</strong> {summary.get('total_cases', 0)}</p>
      <p><strong>Success:</strong> {verdicts.get('success', 0)}</p>
      <p><strong>Suspicious:</strong> {verdicts.get('suspicious', 0)}</p>
      <p><strong>Failed:</strong> {verdicts.get('failed', 0)}</p>
    </div>
    {keyword_table}
    """


def _render_turn(turn: Dict[str, Any]) -> str:
    prompt = html.escape(str(turn.get("prompt", "")))
    response_text = html.escape(str(turn.get("response_text", "")))

    return f"""
    <div class="turn">
      <h4>Turn {turn.get('turn_index', 0)} — Strategy: {html.escape(str(turn.get('strategy', '')))}</h4>
      <p><strong>Status Code:</strong> {turn.get('response_status', 0)}</p>
      <p><strong>Latency:</strong> {turn.get('latency_ms', 0)} ms</p>
      <p><strong>Error:</strong> {html.escape(str(turn.get('error', '')))}</p>

      <details>
        <summary>Prompt</summary>
        <pre>{prompt}</pre>
      </details>

      <details>
        <summary>Request</summary>
        <pre>{_safe_json(turn.get('request_data', {}))}</pre>
      </details>

      <details>
        <summary>Response Text</summary>
        <pre>{response_text}</pre>
      </details>

      <details>
        <summary>Response Data</summary>
        <pre>{_safe_json(turn.get('response_data', {}))}</pre>
      </details>

      <details>
        <summary>Observation</summary>
        <pre>{_safe_json(turn.get('observation', {}))}</pre>
      </details>

      <details>
        <summary>Evaluation</summary>
        <pre>{_safe_json(turn.get('evaluation', {}))}</pre>
      </details>
    </div>
    """


def _render_case(case: Dict[str, Any]) -> str:
    turns_html = "".join(_render_turn(turn) for turn in case.get("turns", []))

    return f"""
    <div class="case">
      <h3>{html.escape(str(case.get('case_id', '')))} — {html.escape(str(case.get('final_verdict', '')))}</h3>
      <p><strong>Category:</strong> {html.escape(str(case.get('category', '')))}</p>
      <p><strong>Goal:</strong> {html.escape(str(case.get('goal', '')))}</p>
      <p><strong>Base Prompt:</strong></p>
      <pre>{html.escape(str(case.get('base_prompt', '')))}</pre>
      <p><strong>Stop Reason:</strong> {html.escape(str(case.get('stop_reason', '')))}</p>
      {turns_html}
    </div>
    """


def generate_html_report_from_jsonl(
    jsonl_path: str | Path,
    html_path: str | Path,
    title: str,
) -> Path:
    jsonl_file = Path(jsonl_path)
    output_file = Path(html_path)

    cases = _load_jsonl(jsonl_file)
    summary = _collect_summary(cases)

    summary_html = _render_summary(summary)
    cases_html = "".join(_render_case(case) for case in cases)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      background: #f7f7f7;
      color: #222;
    }}
    .card, .case {{
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    .turn {{
      border-top: 1px solid #eee;
      padding-top: 12px;
      margin-top: 12px;
    }}
    pre {{
      background: #111;
      color: #f5f5f5;
      padding: 12px;
      overflow-x: auto;
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      margin-bottom: 16px;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 8px;
      text-align: left;
    }}
    th {{
      background: #f0f0f0;
    }}
    details {{
      margin-bottom: 10px;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  {summary_html}
  <h2>Cases</h2>
  {cases_html if cases_html else "<p>No cases found.</p>"}
</body>
</html>
"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(full_html, encoding="utf-8")
    return output_file