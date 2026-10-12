# -*- coding: utf-8 -*-
"""기획안 도식 3종 (matplotlib, 한글 Malgun Gothic)
fig_pipeline.png  : 적응 영수증 분석 파이프라인·검증 설계
fig_calendar.png  : 법정 적응 거버넌스 달력과 산출물 납품 시점
fig_budget_gap.png: 적응 집행 예산 vs 성과검증 예산 공백 + 시나리오 매출
"""
import os, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
OUT = r"C:\for_huss\figures"; os.makedirs(OUT, exist_ok=True)
NAVY, RED, GREEN, GRAY, AMBER, BLUE = "#002060", "#c0392b", "#1e7b4f", "#6b7280", "#b45309", "#1d4ed8"

# ---------- 1. 파이프라인 ----------
fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
box = lambda x, y, w, h, t, fc, ec=None, fs=8, tc="white", bold=True: (ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec or fc, lw=1)), ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", linespacing=1.35))
arrow = lambda x0, y0, x1, y1, c=GRAY: ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=10, color=c, lw=1.2))
box(1, 44, 19, 12, "① 사업 대장\n적응사업 위치·기간·예산", "#e5e7eb", ec="#9ca3af", tc="#111", fs=7.2, bold=False)
box(1, 28, 19, 12, "② 위성 관측 아카이브\nSentinel-1/2 · Landsat\n2017~현재", "#e5e7eb", ec="#9ca3af", tc="#111", fs=7.2, bold=False)
box(1, 12, 19, 12, "③ 수혜 대상 속성\n건축물대장 노후도\nSGIS 고령·1인가구", "#e5e7eb", ec="#9ca3af", tc="#111", fs=7.2, bold=False)
box(27, 35, 27, 21, "A. 효과 검증 엔진\n사업 유형별 위성 지표\n산불복구 → NDVI 회복\n침수 방재 → SAR 침수 범위\n수변 복원 → NDVI·NDMI\n열 저감 → 지표면온도", NAVY, fs=6.6)
box(27, 9, 27, 21, "B. 형평성 감사 엔진\n수혜 건물·필지의 취약도\n(노후·고령·1인가구 비율)\n대 관할 전체 분포 비교", NAVY, fs=6.6)
box(60, 21, 17, 24, "준실험 설계\n동일 궤도·계절 기준선\nrobust z(median/MAD)\n인접 대조군·이중차분\n효과크기·검정력 보고", "#fef3c7", ec=AMBER, tc="#111", fs=6.4, bold=False)
box(83, 44, 16, 12, "이행점검 보고서\n(매년 4/30)", GREEN, fs=7.2)
box(83, 28, 16, 12, "사업별 성과 카드\n출처 배지·한계", GREEN, fs=7.2)
box(83, 12, 16, 12, "공시·평가 첨부\n(공공기관·기업)", GREEN, fs=7.2)
for y in (50, 34, 18): arrow(20, y, 27, 45.5 if y > 30 else 19.5)
arrow(54, 45.5, 60, 38); arrow(54, 19.5, 60, 28)
for y in (50, 34, 18): arrow(77, 33, 83, y)
ax.text(50, 58.6, "집행된 기후적응 사업의 효과와 형평성을 위성 관측으로 사후 검증하는 처리 흐름", ha="center", fontsize=8.5, fontweight="bold", color=NAVY)
ax.text(50, 2, "모든 수치에 OBSERVED / MODEL / RULE / ASSUMPTION 출처 배지를 부여하고, 검출되지 않은 효과는 '미검출'로 보고한다.", ha="center", fontsize=6.6, color="#444")
fig.savefig(os.path.join(OUT, "fig_pipeline.png"), bbox_inches="tight"); fig.savefig(os.path.join(OUT, "fig_pipeline.svg"), bbox_inches="tight"); plt.close(fig)

# ---------- 2. 법정 달력 ----------
fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
ax.set_xlim(0.5, 12.5); ax.set_ylim(0, 5.2); ax.set_yticks([]); ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=8)
for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
rows = [
    (4.3, "지자체 적응대책 이행점검(탄소중립기본법 §40, 시행령 §43)", [(1, 4.0, NAVY, "결과보고서 작성")], 4.0, "4/30 제출"),
    (3.2, "공공기관 적응대책 이행실적(§41, 2026-01 지침: 사업장별 정량화·외부전문가)", [(1, 3.5, NAVY, "이행실적 집계")], 3.5, "상반기 제출"),
    (2.1, "행안부·지자체 여름철 자연재난 대책(폭염은 2018년부터 자연재난)", [(3, 5.0, AMBER, "대책 수립")], 5.0, "5월 전 확정"),
    (1.0, "위성 관측 가용성(생장기·강우기·폭염기)", [(5, 10.0, GREEN, "S-2 생장기 NDVI · S-1 호우 침수 · Landsat 지표면온도")], None, None),
]
for y, label, bars, due, duetxt in rows:
    ax.text(0.55, y + 0.55, label, fontsize=7.2, color="#222", va="bottom")
    for x0, x1, c, t in bars:
        ax.barh(y, x1 - x0, left=x0, height=0.42, color=c, alpha=0.85); ax.text((x0 + x1) / 2, y, t, ha="center", va="center", fontsize=6.6, color="white", fontweight="bold")
    if due: ax.plot([due, due], [y - 0.3, y + 0.3], color=RED, lw=2); ax.text(due + 0.08, y - 0.02, duetxt, fontsize=6.8, color=RED, va="center")
ax.axvspan(1, 3.0, color="#dbeafe", alpha=0.35); ax.text(2.0, 0.3, "납품 창구: 1~3월\n(전년 관측 집계)", ha="center", fontsize=7, color=BLUE, fontweight="bold")
ax.set_title("법정 적응 거버넌스 달력과 산출물 납품 시점", fontsize=9, color=NAVY, loc="left")
fig.savefig(os.path.join(OUT, "fig_calendar.png"), bbox_inches="tight"); fig.savefig(os.path.join(OUT, "fig_calendar.svg"), bbox_inches="tight"); plt.close(fig)

# ---------- 3. 예산 공백 + 시나리오 ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.1), dpi=200, gridspec_kw={"width_ratios": [1.3, 1]})
items = [("기후대응기금\n적응 분야\n(2025)", 1654), ("특교세\n폭염·가뭄\n(2026 여름)", 607.5), ("서울시\n폭염 집행\n(2025)", 359.4), ("환경부\n취약계층\n지원(2025)", 100), ("서울시\n쿨루프\n(2026)", 29), ("성과 검증\n전용 예산", 0)]
xs = np.arange(len(items)); vals = [v for _, v in items]
cols = [NAVY] * 5 + [RED]
a1.bar(xs, vals, color=cols, width=0.6)
for i, v in enumerate(vals): a1.text(i, v + 25, f"{v:,.0f}" if v else "확인된\n항목 없음", ha="center", va="bottom", fontsize=6.6, color=RED if i == 5 else "#222", fontweight="bold" if i == 5 else "normal")
a1.set_xticks(xs); a1.set_xticklabels([k for k, _ in items], fontsize=6.2); a1.set_ylabel("억 원", fontsize=8); a1.set_ylim(0, 1950)
a1.set_title("(a) 적응 집행 예산은 크지만 효과 검증 항목은 없다", fontsize=8.3, loc="left", color=NAVY)
for s in ["top", "right"]: a1.spines[s].set_visible(False)
yrs = ["1년차", "2년차", "3년차"]; low = [0.15, 0.50, 0.70]; base = [0.65, 2.05, 3.94]; high = [1.65, 5.00, 9.58]
a2.fill_between(range(3), low, high, color="#bfdbfe", alpha=0.6, label="하향~상향 범위")
a2.plot(range(3), base, "o-", color=NAVY, lw=2, label="기본 시나리오")
for i, v in enumerate(base): a2.text(i, v + 0.35, f"{v:.2f}", ha="center", fontsize=7, color=NAVY)
a2.set_xticks(range(3)); a2.set_xticklabels(yrs, fontsize=8); a2.set_ylabel("매출(억 원, 계산값)", fontsize=8); a2.set_ylim(0, 10.5)
a2.set_title("(b) 매출 시나리오(가정 명시, 예측 아님)", fontsize=8.3, loc="left", color=NAVY); a2.legend(fontsize=6.8, frameon=False, loc="upper left")
for s in ["top", "right"]: a2.spines[s].set_visible(False)
fig.text(0.01, -0.04, "출처: 국회예산정책처(2025-07-29), 정책브리핑(2026-08-11), 파이낸셜뉴스(2026-08-07), 서울신문(2026-08-18). 시나리오 단가: 적응대책 용역 5,000~6,970만 원(무주·도봉·정읍 공고), 디지털서비스 SaaS 평균 약 4,900만 원/건.", fontsize=6, color="#444")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_budget_gap.png"), bbox_inches="tight"); fig.savefig(os.path.join(OUT, "fig_budget_gap.svg"), bbox_inches="tight"); plt.close(fig)
print("schematics saved")
