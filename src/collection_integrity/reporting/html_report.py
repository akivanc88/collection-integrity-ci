"""Standalone HTML findings report (BUILD_BRIEF.md Section 14, 23).

Self-contained: all CSS and JS are inline, so the file opens from disk with no network access and
no externally hosted assets. Untrusted text (titles, summaries, evidence values) is autoescaped by
Jinja2, addressing the "untrusted HTML in source content" threat-model item. Severity is conveyed
by a text label as well as color, per the accessibility requirement not to rely on color alone.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from collection_integrity.engine.findings import Finding

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Collection Integrity CI report</title>
<style>
  :root { --crit:#a8323f; --high:#b06a24; --medium:#7f7434; --low:#4f6f63; --ink:#1d2529;
    --muted:#5b6560; --line:#d3d5cc; --bg:#f4f4ef; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; line-height:1.5; }
  main { max-width:1000px; margin:0 auto; padding:24px; }
  h1 { font-size:1.6rem; margin:0 0 4px; }
  h2 { font-size:1.15rem; margin:28px 0 10px; border-bottom:1px solid var(--line);
    padding-bottom:4px; }
  .sub { color:var(--muted); font-size:.9rem; margin:0 0 16px; }
  .disclaimer { background:#fff; border:1px solid var(--line); border-left:4px solid var(--high);
    border-radius:8px; padding:12px 16px; font-size:.9rem; }
  table { border-collapse:collapse; width:100%; background:#fff; font-size:.9rem; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line);
    vertical-align:top; }
  th { background:#eeeee8; }
  .sev { font-weight:600; padding:2px 8px; border-radius:6px; font-size:.78rem; color:#fff;
    display:inline-block; }
  .sev-critical{background:var(--crit);} .sev-high{background:var(--high);}
  .sev-medium{background:var(--medium);} .sev-low{background:var(--low);}
  .counts { display:flex; gap:12px; flex-wrap:wrap; list-style:none; padding:0; }
  .counts li { background:#fff; border:1px solid var(--line); border-radius:8px; padding:8px 14px; }
  .counts .n { font-size:1.4rem; font-weight:700; font-variant-numeric:tabular-nums; }
  .filters { margin:8px 0; display:flex; gap:8px; flex-wrap:wrap; }
  .filters button { font:inherit; padding:5px 12px; border:1px solid var(--line);
    background:#fff; border-radius:999px; cursor:pointer; }
  .filters button[aria-pressed="true"] { background:var(--ink); color:#fff; }
  details { margin:2px 0; }
  code { font-family:ui-monospace,Menlo,monospace; font-size:.82rem; }
  .kv { color:var(--muted); }
  .empty { background:#fff; border:1px solid var(--line); border-radius:8px; padding:24px;
    text-align:center; color:var(--muted); }
  .wrap { overflow-x:auto; }
  @media (prefers-color-scheme: dark) {
    :root { --ink:#e8eae4; --muted:#9aa39d; --line:#2b3439; --bg:#12181b; }
    table,.disclaimer,.counts li,.filters button,.empty { background:#1a2125; }
    th { background:#1f272b; }
  }
</style>
</head>
<body>
<main>
  <h1>Collection Integrity CI report</h1>
  <p class="sub">Run {{ manifest.run_id }} &middot; {{ manifest.started_at }} &middot;
    software {{ manifest.software_version }}</p>

  <div class="disclaimer">
    All findings below are <strong>deterministic</strong> checks over the exported data. A
    publication-rights conflict is a policy-consistency warning, not legal advice; a duplicate-file
    or dimension finding is not proof that a record should be deleted. No network access or AI
    provider was used to produce this report
    ({{ "yes" if manifest.network_access_used else "no" }} network,
    {{ "yes" if manifest.ai_providers_used else "no" }} AI).
  </div>

  <h2>Summary</h2>
  <ul class="counts">
    <li><div class="n">{{ findings|length }}</div><div>total findings</div></li>
    {% for sev, n in severity_counts %}
    <li><div class="n">{{ n }}</div><div><span class="sev sev-{{ sev }}">{{ sev }}</span></div></li>
    {% endfor %}
  </ul>
  <p class="sub">Inputs:
    {% for name, n in input_counts %}{{ n }} {{ name }}{{ ", " if not loop.last }}{% endfor %}.</p>

  <h2>Rules evaluated</h2>
  <div class="wrap"><table>
    <thead><tr><th>Rule</th><th>Version</th><th>Findings</th></tr></thead>
    <tbody>
    {% for rid, ver in enabled_rules %}
      <tr><td><code>{{ rid }}</code></td><td>{{ ver }}</td>
        <td>{{ rule_counts.get(rid, 0) }}</td></tr>
    {% endfor %}
    </tbody>
  </table></div>

  <h2>Findings</h2>
  {% if findings %}
  <div class="filters" role="group" aria-label="Filter by severity">
    <button data-sev="all" aria-pressed="true">All</button>
    {% for sev, n in severity_counts %}
    <button data-sev="{{ sev }}" aria-pressed="false">{{ sev }} ({{ n }})</button>
    {% endfor %}
  </div>
  <div class="wrap"><table id="findings">
    <thead><tr><th>Severity</th><th>Rule</th><th>Entity</th><th>Detail</th></tr></thead>
    <tbody>
    {% for f in findings %}
      <tr data-severity="{{ f.severity }}">
        <td><span class="sev sev-{{ f.severity }}">{{ f.severity }}</span></td>
        <td><code>{{ f.rule.id }}</code></td>
        <td>{{ f.entity.type }} <code>{{ f.entity.id }}</code></td>
        <td>
          {{ f.summary }}
          <details>
            <summary>Evidence &amp; remediation</summary>
            <p>{{ f.explanation }}</p>
            <p class="kv">Recommendation: {{ f.recommendation }}</p>
            <ul>
              {% for e in f.evidence %}
              <li class="kv"><code>{{ e.source_file }}</code>
                {% if e.source_row is not none %}row {{ e.source_row }}{% endif %}
                &middot; {{ e.field }} = {{ e.value }}</li>
              {% endfor %}
            </ul>
            <p class="kv">fingerprint <code>{{ f.fingerprint }}</code></p>
          </details>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table></div>
  {% else %}
  <div class="empty">No findings. The scanned data passed every enabled check.</div>
  {% endif %}

  <h2>Provenance</h2>
  <div class="wrap"><table>
    <tbody>
      <tr><th>Command</th><td><code>{{ manifest.command }}</code></td></tr>
      <tr><th>Started</th><td>{{ manifest.started_at }}</td></tr>
      <tr><th>Elapsed (s)</th><td>{{ manifest.elapsed_seconds }}</td></tr>
      {% for path, digest in input_hashes %}
      <tr><th>Input</th><td><code>{{ path }}</code><br>
        <span class="kv">{{ digest }}</span></td></tr>
      {% endfor %}
    </tbody>
  </table></div>
</main>
<script>
  (function () {
    var buttons = document.querySelectorAll('.filters button');
    var rows = document.querySelectorAll('#findings tbody tr');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var sev = btn.getAttribute('data-sev');
        buttons.forEach(function (b) {
          b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
        });
        rows.forEach(function (r) {
          var show = (sev === 'all' || r.getAttribute('data-severity') === sev);
          r.style.display = show ? '' : 'none';
        });
      });
    });
  })();
</script>
</body>
</html>
"""


def render_html_report(
    findings: list[Finding], manifest: dict[str, Any], input_counts: dict[str, int]
) -> str:
    """Render the standalone HTML report as a string."""
    env = Environment(autoescape=select_autoescape(default=True))
    template = env.from_string(_TEMPLATE)

    ordered = sorted(
        findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule.id, f.entity.id)
    )
    severity_counter = Counter(f.severity for f in findings)
    severity_counts = [
        (sev, severity_counter[sev])
        for sev in ("critical", "high", "medium", "low")
        if severity_counter[sev]
    ]
    rule_counts = Counter(f.rule.id for f in findings)
    enabled_rules = [
        (r.get("id", ""), r.get("version", "")) for r in manifest.get("enabled_rules", [])
    ]

    return template.render(
        findings=ordered,
        manifest=manifest,
        severity_counts=severity_counts,
        rule_counts=rule_counts,
        enabled_rules=enabled_rules,
        input_counts=sorted(input_counts.items()),
        input_hashes=sorted(manifest.get("input_hashes", {}).items()),
    )


def write_html_report(
    findings: list[Finding], manifest: dict[str, Any], input_counts: dict[str, int], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html_report(findings, manifest, input_counts), encoding="utf-8")
