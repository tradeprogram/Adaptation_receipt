# -*- coding: utf-8 -*-
"""기획안 모식도 v2 — mechanical-pen-figures §7·§8 학술 모식도 문법(가로 6.8 in, 글자 9.0/8.0/7.2 pt, 직각 꺾은선, 형광펜 1~2곳).

fig_story.png    : 2025 영남 산불 → 복구·복원 → 이행점검의 연대기와 '기록되는 것 / 기록되지 않는 것', 적응 예산 대 성과검증 예산
fig_service.png  : 적응 영수증 서비스 구성도(입력 → 검증 엔진 → 산출물), 실제 위성 썸네일과 실제 영수증 화면
fig_did.png      : (a) 이중차분 설계 개념, (b) 가양8단지 재배분 순위(지붕 100 m²당 세대수)
fig_calendar.png : 법정 적응 거버넌스 달력(재채색)
저장 전 글자 겹침 전수 검사(0건)를 통과해야 한다.
"""
import json, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.transforms import Affine2D
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "figures"; RES = ROOT / "app/cache/results"
plt.rcParams.update({"font.family": ["Arial", "Malgun Gothic"], "axes.unicode_minus": False})
W = 6.8; T_HEAD, T_BODY, T_SMALL = 9.0, 8.0, 7.2
INK, GREY_D, GREY_F, GREY_H = "#1F1F1F", "#404040", "#F2F2F2", "#D9D9D9"
NAVY, RED, BLUE, HL = "#1F3864", "#C00000", "#2F5597", "#FFE45C"
PASTEL = ["#DCE6F2", "#E2EFD9", "#FFF2CC", "#FBE5D6", "#E4DFEC", "#DDEBF7"]
POINT = {"navy": "#1F3A5F", "crimson": "#B4232C", "ochre": "#B8860B", "teal": "#1E7F86", "plum": "#6B4C8A", "grey": "#8C8C8C"}

# 공용 그리기(람다, def 금지 피드백)
canvas = lambda h_in: (lambda fig: (fig, fig.add_axes([0, 0, 1, 1]), 100 * h_in / W))(plt.figure(figsize=(W, h_in)))
sub_axes = lambda fig, H, x, y, w, h: fig.add_axes([x / 100, y / H, w / 100, h / H])
frame = lambda bg, x, y, w, h, title, ec="#7F7F7F", fc=GREY_F: (bg.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=0.8, zorder=0)), bg.text(x + 1.0, y + h - 0.8, title, fontsize=T_HEAD, fontweight="bold", style="italic", color=INK, va="top") if title else None)
proc = lambda bg, x, y, w, h, text, fs=T_BODY, fc="white", ec=GREY_D, tc=INK, weight="normal": (bg.add_patch(patches.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=0.7, zorder=2)), bg.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center", color=tc, fontweight=weight, linespacing=1.3, zorder=3))
header = lambda bg, x, y, w, h, text: (bg.add_patch(patches.Rectangle((x, y), w, h, fc=GREY_H, ec=GREY_D, lw=0.7, zorder=2)), bg.text(x + w / 2, y + h / 2, text, fontsize=T_HEAD, fontweight="bold", ha="center", va="center", color=INK, zorder=3))
hl = lambda bg, x, y, text, fs=T_BODY, ha="left": bg.text(x, y, text, fontsize=fs, fontweight="bold", color=INK, ha=ha, va="center", zorder=6, bbox=dict(boxstyle="square,pad=0.18", fc=HL, ec="none"))
para = lambda bg, x, y, w, h, s, fc, ec=GREY_D, z=2: bg.add_patch(patches.Polygon([(x, y), (x + w, y), (x + w + s, y + h), (x + s, y + h)], closed=True, fc=fc, ec=ec, lw=0.6, zorder=z))
line = lambda bg, pts, color=INK, lw=0.9, arrow=True: (bg.plot([p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]], color=color, lw=lw, solid_capstyle="butt", zorder=4), bg.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, lw=lw, shrinkA=0, shrinkB=0), zorder=4)) if arrow else bg.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, zorder=4)

def_overlap_report = []
check = lambda fig, stem: (fig.canvas.draw(), (lambda r: (lambda items: (lambda boxes: def_overlap_report.append((stem, [(a[0], b[0]) for i, a in enumerate(boxes) for b in boxes[i + 1:] if a[1].overlaps(b[1])])))([(t.get_text().replace("\n", " ")[:28], t.get_window_extent(renderer=r).shrunk(0.94, 0.80)) for t in items if t.get_visible() and t.get_text().strip()]))(list(fig.texts) + [t for ax in fig.axes for t in list(ax.texts) + [ax.title, ax._left_title, ax._right_title] + (list(ax.get_legend().get_texts()) if ax.get_legend() is not None else [])]))(fig.canvas.get_renderer()))
save = lambda fig, stem: (check(fig, stem), fig.savefig(OUT / f"{stem}.png", dpi=280, bbox_inches="tight", pad_inches=0.04, facecolor="white"), plt.close(fig))

# ===================== 1. 사건 연대기와 기록의 공백 =====================
fig, bg, H = canvas(2.15); bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
# (a) 연대기: 왼쪽 62%
bg.text(1, H - 1.2, "(a)", fontsize=T_HEAD, fontweight="bold", va="top")
bg.text(4.5, H - 1.2, "2025년 영남 산불 이후 기록된 것과 기록되지 않은 것", fontsize=T_HEAD, fontweight="bold", va="top")
yl = H - 8.0; x0, x1 = 3, 60
bg.plot([x0, x1], [yl, yl], color=INK, lw=1.2, zorder=3)
events = [(3.0, "2025.03.22", "의성 발화\n03.28 주불 진화"), (16.5, "2025.05.02", "복구계획 확정\n1조 8,809억 원"), (30.0, "2025.10", "국정감사\n복구 실적 1 ha"), (43.5, "2026.04", "복원 기본계획\n계획복원 15%\n자연복원 85%"), (57.0, "2027.04.30", "이행점검 보고서\n제출 기한")]
for x, d, t in events:
    bg.plot([x], [yl], marker="o", ms=5, color=INK, zorder=5)
    bg.text(x, yl + 1.2, d, fontsize=T_SMALL, ha="center", va="bottom", color=GREY_D)
    bg.text(x, yl - 1.3, t, fontsize=T_SMALL, ha="center", va="top", color=INK, linespacing=1.25)
# 기록 여부 띠
frame(bg, 3, 7.0, 57, 7.6, "")
bg.text(4.2, 13.3, "기록되는 것", fontsize=T_BODY, fontweight="bold", va="center", color=INK)
bg.text(21, 13.3, "집행액, 복구 면적, 사업 건수 (집행 증빙)", fontsize=T_BODY, va="center", color=INK)
bg.text(4.2, 9.3, "기록되지 않는 것", fontsize=T_BODY, fontweight="bold", va="center", color=RED)
bg.text(21, 9.3, "피해지가 실제로 회복되었는지, 예산이 취약한 곳에 닿았는지", fontsize=T_BODY, va="center", color=RED)
hl(bg, 4.2, 4.4, "효과 영수증의 공백", fs=T_SMALL)
# (b) 예산 막대: 오른쪽
ax = sub_axes(fig, H, 70, 9.5, 28, H - 16.5)
items = [("기후대응\n기금 적응", 1654), ("특교세\n폭염가뭄", 607.5), ("서울시\n폭염", 359.4), ("환경부\n취약계층", 100), ("성과검증\n전용", 0)]
cols = [POINT["navy"]] * 4 + [RED]
ax.bar(range(5), [v for _, v in items], color=cols, width=0.62, edgecolor="none")
for i, (_, v) in enumerate(items):
    ax.text(i, v + 40, ("0" if v == 0 else f"{v:,.0f}"), ha="center", va="bottom", fontsize=T_SMALL, color=(RED if v == 0 else INK), fontweight=("bold" if v == 0 else "normal"))
ax.set_xticks(range(5)); ax.set_xticklabels([k for k, _ in items], fontsize=6.6)
ax.tick_params(axis="x", length=0, pad=2); ax.tick_params(axis="y", labelsize=T_SMALL)
ax.text(-0.04, 1.03, "억 원", fontsize=T_SMALL, transform=ax.transAxes, va="bottom"); ax.set_ylim(0, 1900)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
bg.text(66, H - 1.2, "(b)", fontsize=T_HEAD, fontweight="bold", va="top")
bg.text(69.5, H - 1.2, "집행 예산과 성과 검증 예산", fontsize=T_HEAD, fontweight="bold", va="top")
save(fig, "fig_story")

# ===================== 2. 서비스 구성도 =====================
fig, bg, H = canvas(3.1); bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
header(bg, 1, H - 4.2, 24, 3.4, "입력 자료"); header(bg, 28, H - 4.2, 44, 3.4, "검증 엔진"); header(bg, 75, H - 4.2, 24, 3.4, "산출물")
# 입력: 사업 대장(평행사변형), 위성 영상 스택(실제 썸네일), 수혜 속성
ty = H - 12.5
para(bg, 2.5, ty, 17, 6.5, 1.8, PASTEL[2]); bg.text(2.5 + 9.4, ty + 3.25, "사업 대장\n위치, 기간, 예산", fontsize=T_BODY, ha="center", va="center", linespacing=1.3, zorder=3)
# 위성 썸네일: 산불 전 진색 합성(실제 자료)
im = Image.open(RES / "fire-uiseong-2025/pre.png").convert("RGB"); im.thumbnail((700, 500)); arr = np.asarray(im)
sx, sy, sw, sh = 2.5, ty - 10.8, 17, 7.4; skew = sh * math.tan(math.radians(16))
for k in (2, 1):
    para(bg, sx + 0.9 * k, sy + 0.9 * k, sw, sh, skew, "white", ec="#8C8C8C", z=1)
tr = Affine2D().translate(-sx, -sy).skew_deg(16, 0).translate(sx, sy) + bg.transData
bg.imshow(arr, extent=(sx, sx + sw, sy, sy + sh), transform=tr, zorder=2, interpolation="antialiased", aspect="auto")
para(bg, sx, sy, sw, sh, skew, "none", ec=GREY_D, z=3)
bg.text(sx + sw / 2 + 1, sy - 1.2, "위성 아카이브\nSentinel-1, Sentinel-2, Landsat", fontsize=T_SMALL, ha="center", va="top", linespacing=1.25, color=GREY_D)
py = sy - 12.6
para(bg, 2.5, py, 17, 6.5, 1.8, PASTEL[1]); bg.text(2.5 + 9.4, py + 3.25, "수혜 대상 속성\n건축물대장, 통계청 SGIS", fontsize=T_BODY, ha="center", va="center", linespacing=1.3, zorder=3)
# 버스선 → 엔진
for yy in (ty + 3.25, sy + sh / 2, py + 3.25):
    bg.plot([21.5, 25.0], [yy, yy], color=INK, lw=0.9, zorder=4)
bg.plot([25.0, 25.0], [py + 3.25, ty + 3.25], color=INK, lw=0.9, zorder=4)
line(bg, [(25.0, sy + sh / 2), (28, sy + sh / 2)])
# 엔진 틀(머리띠 아래부터 남색 블록 아래까지)
ex, ew = 30, 40
y1, y2, y3, y4 = H - 11.6, H - 17.6, H - 23.6, H - 29.6          # 단계 상자 아래변
yn = H - 38.0                                                       # 남색 블록 아래변
frame(bg, 28, yn - 1.6, 44, (H - 4.8) - (yn - 1.6), "")
proc(bg, ex, y1, ew, 6.0, "1. 사업 유형별 위성 지표 산출\n산불: dNBR, NDVI 회복률  |  침수: SAR 범위\n열: 여름 지표면온도", fs=T_SMALL)
proc(bg, ex, y2, ew, 4.6, "2. 같은 궤도, 같은 계절의 기준선\n인접 대조구 설정", fs=T_SMALL)
bg.add_patch(patches.Rectangle((ex, y3), ew, 4.6, fc="white", ec=GREY_D, lw=0.7, zorder=2))
hl(bg, ex + ew / 2, y3 + 2.3, "3. 사업 전후 이중차분\n신뢰구간, 검출가능최소효과", fs=T_SMALL, ha="center")
proc(bg, ex, y4, ew, 4.6, "4. 형평성 감사, 다음 집행 순위\n노후도, 고령, 세대수", fs=T_SMALL)
proc(bg, ex, yn, ew, 6.6, "성과 카드 조립\n출처 배지(실측, 계산, 규칙, 가정)\n판정(검출, 미검출, 측정 불가)", fs=T_SMALL, fc=NAVY, ec=NAVY, tc="white", weight="bold")
for ya, yb in ((y1, y2 + 4.6), (y2, y3 + 4.6), (y3, y4 + 4.6), (y4, yn + 6.6)):
    line(bg, [(ex + ew / 2, ya), (ex + ew / 2, yb)])
# 엔진 → 산출물
rx, ry, rw, rh = 75, H - 29.0, 23, 23.0
nc = yn + 3.3
bg.plot([70, 73], [nc, nc], color=INK, lw=0.9, zorder=4)
bg.plot([73, 73], [nc - 4.8, ry + rh / 2], color=INK, lw=0.9, zorder=4)
line(bg, [(73, ry + rh / 2), (rx, ry + rh / 2)])
line(bg, [(73, nc + 1.2), (rx, nc + 1.2)]); line(bg, [(73, nc - 4.8), (rx, nc - 4.8)])
# 산출물: 실제 영수증 화면(굵은 둥근 틀), 이행점검 부록, 공시 첨부
bg.add_patch(patches.FancyBboxPatch((rx, ry), rw, rh, boxstyle="round,pad=0,rounding_size=1.0", fc="white", ec=INK, lw=1.8, zorder=2))
ui = Image.open(OUT / "fig_ui_dashboard.png").convert("RGB").crop((1880, 160, 3160, 1990)); ui.thumbnail((520, 740))
axr = sub_axes(fig, H, rx + 1.2, ry + 1.0, rw - 2.4, rh - 5.2); axr.imshow(np.asarray(ui), interpolation="antialiased"); axr.axis("off")
bg.text(rx + rw / 2, ry + rh - 2.1, "성과 카드(영수증)", fontsize=T_BODY, fontweight="bold", color=RED, ha="center", va="center", zorder=5)
proc(bg, rx, nc + 1.2 - 2.2, rw, 4.4, "이행점검 보고서 부록\n매년 4월 30일 제출", fs=T_SMALL)
proc(bg, rx, nc - 4.8 - 2.2, rw, 4.4, "공시, 경영평가 첨부\n공공기관, 상장기업", fs=T_SMALL)
save(fig, "fig_service")

# ===================== 3. 이중차분 개념 + 재배분 순위 =====================
fig = plt.figure(figsize=(W, 2.9))
a1 = fig.add_axes([0.07, 0.17, 0.40, 0.70]); a2 = fig.add_axes([0.58, 0.17, 0.40, 0.70])
# (a) 개념도: 처리구·대조구의 사업 전후
a1.plot([0, 1], [1.00, 0.72], color=POINT["crimson"], lw=2.0, marker="o", ms=5, label="처리구(사업 시행)")
a1.plot([0, 1], [1.00, 0.92], color=POINT["teal"], lw=2.0, marker="s", ms=5, ls="--", label="대조구(인접 미시행)")
a1.plot([1, 1], [0.72, 0.92], color=INK, lw=0.9); a1.plot([0.985, 1.015], [0.72, 0.72], color=INK, lw=0.9); a1.plot([0.985, 1.015], [0.92, 0.92], color=INK, lw=0.9)
a1.text(1.04, 0.82, "효과\n= 차이의 차이", fontsize=T_SMALL, va="center", color=INK, linespacing=1.25)
a1.text(0.5, 1.02, "계절, 기상, 전체 추세는 두 구역이 함께 겪음", fontsize=T_SMALL, ha="center", color=GREY_D)
a1.set_xlim(-0.12, 1.42); a1.set_ylim(0.6, 1.12); a1.set_xticks([0, 1]); a1.set_xticklabels(["사업 전", "사업 후"], fontsize=T_BODY); a1.set_yticks([])
a1.set_ylabel("위성 지표(온도, 식생, 침수)", fontsize=T_SMALL)
a1.legend(loc="lower left", frameon=False, fontsize=T_SMALL)
for s in ("top", "right"):
    a1.spines[s].set_visible(False)
a1.text(-0.12, 1.19, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); a1.text(-0.02, 1.19, "처리구 대 대조구의 사업 전후 비교", fontsize=T_HEAD, fontweight="bold", va="top")
# (b) 가양8단지 재배분 순위
eq = json.loads((RES / "heat-gayang8-coolroof/heat.json").read_text(encoding="utf-8"))
rows = [("809동", 11.42, "후보"), ("807동", 9.82, "후보"), ("808동", 8.57, "후보"), ("802동", 7.00, "후보"), ("805동", 6.55, "후보"), ("801동", 5.36, "시공"), ("803동", 5.03, "대조"), ("804동", 4.65, "시공"), ("806동", 4.65, "후보")]
col = {"후보": POINT["navy"], "시공": POINT["crimson"], "대조": POINT["grey"]}
a2.barh(range(len(rows))[::-1], [r[1] for r in rows], color=[col[r[2]] for r in rows], height=0.62, edgecolor="none")
a2.set_yticks(range(len(rows))[::-1]); a2.set_yticklabels([r[0] for r in rows], fontsize=T_SMALL)
for i, r in enumerate(rows):
    a2.text(r[1] + 0.15, len(rows) - 1 - i, f"{r[1]:.1f}", va="center", fontsize=T_SMALL, color=INK)
a2.set_xlim(0, 14); a2.set_xlabel("지붕 100 m²당 세대수", fontsize=T_SMALL); a2.tick_params(axis="x", labelsize=T_SMALL)
for s in ("top", "right"):
    a2.spines[s].set_visible(False)
h_ = [patches.Patch(color=col[k], label=k) for k in ("후보", "시공", "대조")]
a2.legend(handles=h_, loc="lower right", frameon=False, fontsize=T_SMALL)
a2.text(-0.24, 1.08, "(b)", fontsize=T_HEAD, fontweight="bold", va="top", transform=a2.transAxes); a2.text(-0.10, 1.08, "가양8단지 9개 동의 다음 집행 순위", fontsize=T_HEAD, fontweight="bold", va="top", transform=a2.transAxes)
save(fig, "fig_did")

# ===================== 4. 법정 달력(재채색) =====================
fig, ax = plt.subplots(figsize=(W, 2.6))
months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
ax.set_xlim(0.5, 12.5); ax.set_ylim(0, 5.3); ax.set_yticks([]); ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=T_SMALL)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
rows = [(4.35, "지자체 적응대책 이행점검(탄소중립기본법 제40조)", [(1, 4.0, POINT["navy"], "결과보고서 작성")], 4.0, "4월 30일 제출"),
        (3.25, "공공기관 적응대책 이행실적(제41조, 2026년 1월 지침)", [(1, 3.5, POINT["navy"], "이행실적 집계")], 3.5, "상반기 제출"),
        (2.15, "지자체 여름철 자연재난 대책(폭염 포함)", [(3, 5.0, POINT["ochre"], "대책 수립")], 5.0, "5월 전 확정"),
        (1.05, "위성 관측 가용 시기", [(5, 10.0, POINT["teal"], "생장기 식생, 호우 침수, 폭염기 지표면온도")], None, None)]
for y, label, bars, due, duetxt in rows:
    ax.text(0.55, y + 0.52, label, fontsize=T_SMALL, color=INK, va="bottom")
    for x0, x1, c, t in bars:
        ax.barh(y, x1 - x0, left=x0, height=0.42, color=c, alpha=0.9); ax.text((x0 + x1) / 2, y, t, ha="center", va="center", fontsize=T_SMALL, color="white", fontweight="bold")
    if due:
        ax.plot([due, due], [y - 0.3, y + 0.3], color=RED, lw=2); ax.text(due + 0.1, y - 0.02, duetxt, fontsize=T_SMALL, color=RED, va="center")
ax.axvspan(1, 3.0, color=PASTEL[0], alpha=0.6, zorder=0); ax.text(2.0, 0.28, "납품 창구: 1월부터 3월(전년 관측 집계)", ha="center", fontsize=T_SMALL, color=BLUE, fontweight="bold")
save(fig, "fig_calendar")

for stem, hits in def_overlap_report:
    print(stem, "겹침", len(hits), hits[:6])
