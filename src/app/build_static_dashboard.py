# Polished static Plotly dashboard -> docs/index.html (+ dashboard.html)
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px

OUT = Path("reports/figures")
DOCS = Path("docs"); DOCS.mkdir(parents=True, exist_ok=True)

# --- Load data exported in Step 2 ---
prog_pass = pd.read_csv(OUT/"kpi_pass_rate.csv")
turn      = pd.read_csv(OUT/"assessment_turnaround_bins.csv")
eng       = pd.read_csv(OUT/"engagement_index.csv")
risk      = pd.read_csv(OUT/"at_risk_modules.csv")
if "at_risk" in risk.columns and risk["at_risk"].dtype != bool:
    risk["at_risk"] = risk["at_risk"].astype(bool)

# Term ordering for nicer lines
term_order = ["2023-Fall","2024-Spring","2024-Fall","2025-Spring"]
if "term" in prog_pass.columns:
    prog_pass["term"] = pd.Categorical(prog_pass["term"], categories=term_order, ordered=True)

# Join for scatter (programme/term)
merged = prog_pass.merge(
    eng[["programme","term","engagement_index","mean_score_1_5"]],
    on=["programme","term"], how="left"
)

# ---------- KPI cards ----------
overall_pass   = prog_pass["pass_rate_pct"].mean()        # mean across programme/term
pct_turn_le_15 = (turn["turn_bin"].isin(["<=10","11-15"]).mean()*100) if "turn_bin" in turn.columns else np.nan
eng_median     = eng["engagement_index"].median()
at_risk_count  = int(risk["at_risk"].sum())

kpi_cards = [
    ("Overall pass rate",            f"{overall_pass:0.1f}%"),
    ("Assessments returned ≤15d",    f"{pct_turn_le_15:0.0f}%"),
    ("Median engagement index",      f"{eng_median:0.2f}"),
    ("At‑risk modules",              f"{at_risk_count}"),
]

# ---------- Figures ----------
# 1) Programme pass rates
fig1 = px.line(prog_pass.sort_values(["programme","term"]),
               x="term", y="pass_rate_pct", color="programme",
               markers=True, title="Programme Pass Rates by Term")
fig1.update_layout(yaxis_title="Pass rate (%)")

# 2) Assessment turnaround distribution
order = ["<=10","11-15","16-20",">20"]
if "turn_bin" in turn.columns:
    turn["turn_bin"] = pd.Categorical(turn["turn_bin"], categories=order, ordered=True)
turn_counts = turn["turn_bin"].value_counts().sort_index().rename_axis("bin").reset_index(name="count")
fig2 = px.bar(turn_counts, x="bin", y="count", title="Assessment Turnaround Distribution")

# 3) Engagement vs pass (each dot = programme/term)
fig3 = px.scatter(merged, x="engagement_index", y="pass_rate_pct",
                  color="programme", hover_data=["programme","term"],
                  title="Engagement vs Pass Rate (each dot = programme/term)")
fig3.update_layout(xaxis_title="Engagement index", yaxis_title="Pass rate (%)")

# 4) Module pass vs satisfaction (each dot = module)
risk["color"] = risk["at_risk"].map({True:"Low satisfaction & pass (at‑risk)", False:"Higher satisfaction"})
fig4 = px.scatter(risk, x="mean_survey", y="pass_rate",
                  color="color", hover_data=["module_id"],
                  title="Modules: Pass vs Survey Satisfaction (each dot = module)")
fig4.update_layout(xaxis_title="Survey score (1–5)", yaxis_title="Pass rate (%)")

# 5) Segment #5 (≤ medians for engagement & pass)
cut_eng = merged["engagement_index"].median()
cut_pass_prog = merged["pass_rate_pct"].median()
seg5 = merged[(merged["engagement_index"] <= cut_eng) & (merged["pass_rate_pct"] <= cut_pass_prog)]
fig5 = px.scatter(seg5, x="engagement_index", y="pass_rate_pct",
                  color="programme", hover_data=["programme","term"],
                  title=f"Segment #5: Medium‑to‑Low Engagement & Pass (≤ medians: {cut_eng:.2f}, {cut_pass_prog:.1f}%)")
fig5.add_vline(x=cut_eng, line_dash="dash"); fig5.add_hline(y=cut_pass_prog, line_dash="dash")
fig5.update_layout(xaxis_title="Engagement index", yaxis_title="Pass rate (%)")

# 6) Segment #6 (modules with medium‑to‑low pass)
cut_pass_mod = risk["pass_rate"].median()
seg6 = risk[risk["pass_rate"] <= cut_pass_mod].copy()
seg6["Satisfaction"] = np.where(seg6["mean_survey"] <= risk["mean_survey"].median(),
                                "Low survey (≤ median)","Higher survey")
fig6 = px.scatter(seg6, x="mean_survey", y="pass_rate",
                  color="Satisfaction", hover_data=["module_id"],
                  title=f"Segment #6: Modules with Medium‑to‑Low Pass (≤ median: {cut_pass_mod:.1f}%)")
fig6.add_hline(y=cut_pass_mod, line_dash="dash")
fig6.update_layout(xaxis_title="Survey score (1–5)", yaxis_title="Pass rate (%)")

# ---------- HTML shell with simple CSS ----------
CSS = """
<style>
  :root { --bg:#0b132b; --card:#1c2541; --ink:#eaeff7; --muted:#a9b7d0; --accent:#5bc0be; }
  *{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:var(--bg);color:var(--ink)}
  header{padding:48px 24px 16px;text-align:center}
  header h1{margin:0;font-size:34px}
  header p{color:var(--muted);margin:8px 0 0}
  .container{max-width:1200px;margin:0 auto;padding:24px}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:8px 0 24px}
  .card{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  .kpis .card h3{margin:0;font-size:13px;color:var(--muted);letter-spacing:.3px}
  .kpis .card div{font-size:26px;margin-top:6px;color:var(--ink)}
  h2{margin:24px 0 6px;font-size:20px}
  .caption{color:var(--muted);font-size:13px;margin-top:4px;margin-bottom:16px}
  .grid{display:grid;grid-template-columns:1fr;gap:22px}
  @media (min-width: 900px){ .grid{grid-template-columns:1fr 1fr} }
  footer{color:var(--muted);text-align:center;padding:32px 0 48px}
  a.btn{display:inline-block;margin-top:8px;padding:10px 14px;border-radius:10px;background:var(--accent);color:#102a43;text-decoration:none;font-weight:600}
</style>
"""

def sec(title, fig, caption=None):
    html = [f"<h2>{title}</h2>"]
    if caption: html += [f"<div class='caption'>{caption}</div>"]
    html += [fig.to_html(full_html=False, include_plotlyjs=False)]
    return "\n".join(html)

# Compose index.html (landing)
parts = [
  "<!doctype html><html><head><meta charset='utf-8'>",
  "<meta name='viewport' content='width=device-width, initial-scale=1'/>",
  "<title>Quality Enhancement Dashboard</title>",
  "<link rel='preconnect' href='https://fonts.googleapis.com'><link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap' rel='stylesheet'>",
  "<script src='https://cdn.plot.ly/plotly-2.34.0.min.js'></script>",
  CSS,
  "</head><body>",
  "<header><h1>Quality Enhancement Dashboard</h1>",
  "<p>All data are synthetic. Built with pandas + Plotly. Aligned to QAA UK themes.</p></header>",
  "<div class='container'>",
  "<div class='kpis'>",
] + [f"<div class='card'><h3>{k}</h3><div>{v}</div></div>" for k,v in kpi_cards] + [
  "</div>",
  "<div class='grid'>",
  "<div class='card'>", sec("Programme Pass Rates by Term", fig1), "</div>",
  "<div class='card'>", sec("Assessment Turnaround Distribution", fig2, "Each bar = count of assessments in the turnaround bin."), "</div>",
  "<div class='card'>", sec("Engagement vs Pass Rate", fig3, "Each dot = a programme/term combination."), "</div>",
  "<div class='card'>", sec("Modules: Pass vs Survey Satisfaction", fig4, "Each dot = a module. Red = low satisfaction & pass."), "</div>",
  "<div class='card'>", sec("Segment #5: Medium‑to‑Low Engagement & Pass", fig5), "</div>",
  "<div class='card'>", sec("Segment #6: Modules with Medium‑to‑Low Pass", fig6), "</div>",
  "</div>",
  "<div style='text-align:center'><a class='btn' href='dashboard.html'>Open full dashboard page</a></div>",
  "</div>",
  "<footer>© 2025 • Quality Enhancement Analytics • Synthetic data for demo only</footer>",
  "</body></html>"
]
(DOCS/"index.html").write_text("\n".join(parts), encoding="utf-8")

# Also write a simple dashboard.html (same content without KPI cards if you want)
(DOCS/"dashboard.html").write_text("\n".join(parts), encoding="utf-8")

print("[OK] Wrote docs/index.html and docs/dashboard.html")