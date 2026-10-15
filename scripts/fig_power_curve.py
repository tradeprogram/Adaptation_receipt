"""그림: 처리 면적에 따른 검출가능최소효과(MDE) — 가양8단지 Landsat 지표면온도 대조 분산 실측값 기준.

n = 2((zα+zβ)σ/δ)²  ↔  δ(MDE) = (zα+zβ)σ√(2/n),  n = 처리 30 m 화소 수, 1 화소 = 0.09 ha.
입력: app/cache/results/heat-gayang8-coolroof/heat.json (design.control_sd_c, metrics.treated_area_ha, mde_c)
출력: figures/fig_power_curve.png / .svg
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / "app/cache/results/heat-gayang8-coolroof/heat.json").read_text(encoding="utf-8"))
sd = r["design"]["control_sd_c"]; treated_ha = r["metrics"]["treated_area_ha"]["value"]; mde_now = r["metrics"]["mde_c"]["value"]
z = 1.96 + 0.84; px_ha = 0.09

plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 9})
fig, ax = plt.subplots(figsize=(5.6, 2.9), dpi=200)
area = np.linspace(0.2, 12, 400)
n = area / px_ha
mde = z * sd * np.sqrt(2.0 / n)
ax.plot(area, mde, color="#1F3A5F", lw=2, label=f"MDE(σ = {sd:.2f}℃, 80% 검정력, α = 0.05)")
for d, lab, c in ((1.0, "1℃", "#C9A227"), (0.5, "0.5℃", "#8a5a1e")):
    a_need = 2 * (z * sd / d) ** 2 * px_ha
    ax.axhline(d, color=c, lw=0.9, ls="--")
    ax.plot([a_need], [d], "o", color=c, ms=5)
    ax.annotate(f"{lab} 검출에 {a_need:.2f} ha", (a_need, d), xytext=(8, 6), textcoords="offset points", color=c, fontsize=8.5)
ax.plot([treated_ha], [mde_now], "s", color="#B03A2E", ms=6)
ax.annotate(f"가양8단지 801·804동\n{treated_ha:.2f} ha → MDE {mde_now:.2f}℃", (treated_ha, mde_now), xytext=(14, 10), textcoords="offset points", color="#B03A2E", fontsize=8.5)
ax.set_xlabel("처리(시공) 면적 (ha)"); ax.set_ylabel("검출가능최소효과 (℃)")
ax.set_xlim(0, 12); ax.set_ylim(0, 3.2); ax.grid(alpha=0.25, lw=0.5)
ax.legend(loc="upper right", frameon=False, fontsize=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(ROOT / "figures/fig_power_curve.png"); fig.savefig(ROOT / "figures/fig_power_curve.svg")
print("saved", sd, treated_ha, mde_now)
