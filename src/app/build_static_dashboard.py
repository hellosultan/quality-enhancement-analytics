# Builds a static Plotly dashboard from exported CSVs → docs/dashboard.html
import pandas as pd
from pathlib import Path
import plotly.express as px
import numpy as np

outdir = Path("reports/figures")
docs = Path("docs"); docs.mkdir(exist_ok=True, parents=True)

# Load CSVs (make sure Step 2 exports exist)
prog_pass = pd.read_csv(outdir/"kpi_pass_rate.csv")
turn      = pd.read_csv(outdir/"assessment_turnaround_bins.csv")
eng       = pd.read_csv(outdir/"engagement_index.csv")
risk      = pd.read_csv(outdir/"at_risk_modules.csv")
if "at_risk" in risk.columns and risk["at_risk"].dtype != bool:
    risk["at_risk"] = risk["at_risk"].astype(bool)

# Order terms for nicer lines
term_order = ["2023-Fall","2024-Spring","2024-Fall","2025-Spring"]
if "term" in prog_pass.columns:
    prog_pass["term"] = pd.Categorical(prog_pass["term"], categories=term_order, ordered=True)

# Merge engagement for scatter #3
merged = prog_pass.merge(
    eng[["programme","term","mean_score_1_5","engagement_index"]],
    on=["programme","term"], how="left"
)

# 1) Programme pass rates
fig1 = px.line(
    prog_pass.sort_values(["programme","term"]),
    x="term", y="pass_rate_pct", color="programme",
    markers=True, title="Programme Pass Rates by Term"
)
fig1.update_layout(yaxis_title="Pass rate (%)")

# 2) Assessment turnaround distribution
order = ["<=10","11-15","16-20",">20"]
if "turn_bin" in turn.columns:
    turn["turn_bin"] = pd.Categorical(turn["turn_bin"], categories=order, ordered=True)
turn_counts = turn["turn_bin"].value_counts().sort_index().rename_axis("bin").reset_index(name="count")
fig2 = px.bar(turn_counts, x="bin", y="count", title="Assessment Turnaround Distribution")

# 3) Engagement vs Pass (each dot = programme/term)
fig3 = px.scatter(
    merged, x="engagement_index", y="pass_rate_pct",
    color="programme", hover_data=["programme","term"],
    title="Engagement vs Pass Rate (each dot = programme/term)"
)
fig3.update_layout(xaxis_title="Engagement index", yaxis_title="Pass rate (%)")

# 4) Modules: pass vs satisfaction (each dot = module)
risk["color"] = risk["at_risk"].map({True:"Low satisfaction & pass (at-risk)", False:"Higher satisfaction"})
fig4 = px.scatter(
    risk, x="mean_survey", y="pass_rate",
    color="color", hover_data=["module_id"],
    title="Modules: Pass vs Survey Satisfaction (each dot = module)"
)
fig4.update_layout(xaxis_title="Survey score (1–5)", yaxis_title="Pass rate (%)")

# 5) Segment #5 (medium-to-low engagement & pass)
cut_eng = merged["engagement_index"].median()
cut_pass_prog = merged["pass_rate_pct"].median()
seg5 = merged[(merged["engagement_index"] <= cut_eng) & (merged["pass_rate_pct"] <= cut_pass_prog)]
fig5 = px.scatter(
    seg5, x="engagement_index", y="pass_rate_pct",
    color="programme", hover_data=["programme","term"],
    title=f"Segment #5: Medium-to-Low Engagement & Pass (≤ medians: {cut_eng:.2f}, {cut_pass_prog:.1f}%)"
)
fig5.add_vline(x=cut_eng, line_dash="dash")
fig5.add_hline(y=cut_pass_prog, line_dash="dash")

# 6) Segment #6 (modules with medium-to-low pass)
cut_pass_mod = risk["pass_rate"].median()
seg6 = risk[risk["pass_rate"] <= cut_pass_mod].copy()
seg6["Satisfaction"] = np.where(
    seg6["mean_survey"] <= risk["mean_survey"].median(),
    "Low survey (≤ median)", "Higher survey"
)
fig6 = px.scatter(
    seg6, x="mean_survey", y="pass_rate",
    color="Satisfaction", hover_data=["module_id"],
    title=f"Segment #6: Modules with Medium-to-Low Pass (≤ median: {cut_pass_mod:.1f}%)"
)
fig6.add_hline(y=cut_pass_mod, line_dash="dash")
fig6.update_layout(xaxis_title="Survey score (1–5)", yaxis_title="Pass rate (%)")

# Compose into a simple HTML page
sections = [
    ("Programme Pass Rates by Term", fig1),
    ("Assessment Turnaround Distribution", fig2),
    ("Engagement vs Pass Rate (programme/term)", fig3),
    ("Modules: Pass vs Survey Satisfaction", fig4),
    ("Segment #5: Medium-to-Low Engagement & Pass", fig5),
    ("Segment #6: Modules with Medium-to-Low Pass", fig6),
]

html_parts = [
    "<html><head><meta charset='utf-8'><title>Quality Enhancement Dashboard</title></head><body>",
    "<h1>Quality Enhancement Dashboard</h1>",
    "<p>All data are synthetic and for demonstration only.</p>",
]
for title, fig in sections:
    html_parts.append(f"<h2>{title}</h2>")
    html_parts.append(fig.to_html(full_html=False, include_plotlyjs='cdn'))
html_parts.append("</body></html>")

(docs := Path("docs")).mkdir(exist_ok=True, parents=True)
(docs/"dashboard.html").write_text("\n".join(html_parts), encoding="utf-8")
print("[OK] Wrote docs/dashboard.html")