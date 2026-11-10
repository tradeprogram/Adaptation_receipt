# -*- coding: utf-8 -*-
"""기획안 모식도 v2 — mechanical-pen-figures §7·§8 학술 모식도 문법(가로 6.8 in, 글자 9.0/8.0/7.2 pt, 직각 꺾은선, 형광펜 1~2곳).

fig_story.png    : 2025 영남 산불 → 복구·복원 → 이행점검의 연대기와 '기록되는 것 / 기록되지 않는 것', 적응 예산 대 성과검증 예산
fig_service.png  : 적응 영수증 서비스 구성도(입력 → 검증 엔진 → 산출물), 실제 위성 썸네일과 실제 영수증 화면
fig_did.png      : (a) 이중차분 설계 개념, (b) 가양8단지 재배분 순위(지붕 100 m²당 세대수)
fig_calendar.png : 법정 적응 거버넌스 달력(재채색)
fig_ui_crop.png  : 시제품 화면 상단(지도와 영수증) 잘라내기
저장 전 글자 겹침 전수 검사(0건)와 글자 상자가 도형 밖으로 나가지 않았는지 검사(0건)를 통과해야 한다.
"""
import json, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.transforms import Affine2D, Bbox
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "figures"; RES = ROOT / "app/cache/results"
plt.rcParams.update({"font.family": ["Arial", "Malgun Gothic"], "axes.unicode_minus": False})
W = 6.8; T_HEAD, T_BODY, T_SMALL = 9.0, 8.0, 7.2
INK, GREY_D, GREY_F, GREY_H = "#1F1F1F", "#404040", "#F2F2F2", "#D9D9D9"
NAVY, RED, BLUE, HL = "#1F3864", "#C00000", "#2F5597", "#FFE45C"
PASTEL = ["#DCE6F2", "#E2EFD9", "#FFF2CC", "#FBE5D6", "#E4DFEC", "#DDEBF7"]
POINT = {"navy": "#1F3A5F", "crimson": "#B4232C", "ochre": "#B8860B", "teal": "#1E7F86", "plum": "#6B4C8A", "grey": "#8C8C8C"}

# 공용 그리기(람다, def 금지 피드백). boxes_log에 (글자, 상자) 쌍을 기록해 글자가 상자 밖으로 나갔는지 검사한다
boxes_log = []
canvas = lambda h_in: (lambda fig: (fig, fig.add_axes([0, 0, 1, 1]), 100 * h_in / W))(plt.figure(figsize=(W, h_in)))
sub_axes = lambda fig, H, x, y, w, h: fig.add_axes([x / 100, y / H, w / 100, h / H])
frame = lambda bg, x, y, w, h, title, ec="#7F7F7F", fc=GREY_F: (bg.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=0.8, zorder=0)), bg.text(x + 1.2, y + h - 0.9, title, fontsize=T_HEAD, fontweight="bold", style="italic", color=INK, va="top") if title else None)
proc = lambda bg, x, y, w, h, text, fs=T_BODY, fc="white", ec=GREY_D, tc=INK, weight="normal": (bg.add_patch(patches.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=0.7, zorder=2)), boxes_log.append((bg.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center", color=tc, fontweight=weight, linespacing=1.3, zorder=3), (x, y, w, h))))
header = lambda bg, x, y, w, h, text: (bg.add_patch(patches.Rectangle((x, y), w, h, fc=GREY_H, ec=GREY_D, lw=0.7, zorder=2)), bg.text(x + w / 2, y + h / 2, text, fontsize=T_HEAD, fontweight="bold", ha="center", va="center", color=INK, zorder=3))
hl = lambda bg, x, y, text, fs=T_BODY, ha="left": bg.text(x, y, text, fontsize=fs, fontweight="bold", color=INK, ha=ha, va="center", zorder=6, linespacing=1.3, bbox=dict(boxstyle="square,pad=0.18", fc=HL, ec="none"))
para = lambda bg, x, y, w, h, s, fc, ec=GREY_D, z=2: bg.add_patch(patches.Polygon([(x, y), (x + w, y), (x + w + s, y + h), (x + s, y + h)], closed=True, fc=fc, ec=ec, lw=0.6, zorder=z))
line = lambda bg, pts, color=INK, lw=0.9, arrow=True: (bg.plot([p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]], color=color, lw=lw, solid_capstyle="butt", zorder=4), bg.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, lw=lw, shrinkA=0, shrinkB=0), zorder=4)) if arrow else bg.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, zorder=4)

report = []
texts_of = lambda fig: [t for ax in fig.axes for t in list(ax.texts) + [ax.title] + (list(ax.get_legend().get_texts()) if ax.get_legend() is not None else []) if t.get_visible() and t.get_text().strip()]
bbx = lambda t, r: t.get_window_extent(renderer=r).shrunk(0.94, 0.80)
overlaps = lambda fig, r: (lambda L: [(a.get_text().replace("\n", " ")[:24], b.get_text().replace("\n", " ")[:24]) for i, a in enumerate(L) for b in L[i + 1:] if bbx(a, r).overlaps(bbx(b, r))])(texts_of(fig))
boxpx = lambda bg, x, y, w, h: Bbox.from_extents(*bg.transData.transform((x, y)), *bg.transData.transform((x + w, y + h)))
outside = lambda fig, bg, r: [t.get_text().replace("\n", " ")[:24] for t, (x, y, w, h) in boxes_log if t.figure is fig and not (boxpx(bg, x, y, w, h).contains(*t.get_window_extent(renderer=r).min) and boxpx(bg, x, y, w, h).contains(*t.get_window_extent(renderer=r).max))]
check = lambda fig, bg, stem: (fig.canvas.draw(), report.append((stem, "겹침", overlaps(fig, fig.canvas.get_renderer()))), report.append((stem, "상자밖", outside(fig, bg, fig.canvas.get_renderer()))))
save = lambda fig, bg, stem: (check(fig, bg, stem), fig.savefig(OUT / f"{stem}.png", dpi=280, bbox_inches="tight", pad_inches=0.04, facecolor="white"), plt.close(fig))

# ===================== 1. 사건 연대기와 기록의 공백 =====================
fig, bg, H = canvas(1.95); bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
bg.text(1, H - 1.0, "(a)", fontsize=T_HEAD, fontweight="bold", va="top")
bg.text(4.5, H - 1.0, "2025년 영남 산불 이후 기록된 것과 기록되지 않은 것", fontsize=T_HEAD, fontweight="bold", va="top")
yl = H - 7.6; xs_ev = [4, 27, 50, 73, 96]
bg.plot([xs_ev[0], xs_ev[-1]], [yl, yl], color=INK, lw=1.2, zorder=3)
events = [("2025.03.22", "의성 발화\n03.28 주불 진화"), ("2025.05.02", "복구계획 확정\n1조 8,809억 원"), ("2025.10", "국정감사\n복구 실적 1 ha"), ("2026.04", "복원 기본계획\n계획복원 15%, 자연복원 85%"), ("2027.04.30", "이행점검 보고서\n제출 기한")]
for x, (d, t) in zip(xs_ev, events):
    bg.plot([x], [yl], marker="o", ms=5, color=INK, zorder=5)
    bg.text(x, yl + 1.2, d, fontsize=T_SMALL, ha="center", va="bottom", color=GREY_D)
    bg.text(x, yl - 1.4, t, fontsize=T_SMALL, ha="center", va="top", color=INK, linespacing=1.25)
# 왼쪽: 기록 여부 틀(제목은 틀 안 형광펜)
fx, fy, fw, fh = 2, 1.0, 52, 12.2
frame(bg, fx, fy, fw, fh, "")
hl(bg, fx + 1.6, fy + fh - 1.9, "효과 영수증의 공백", fs=T_SMALL)
bg.text(fx + 1.6, fy + 7.2, "기록되는 것", fontsize=T_BODY, fontweight="bold", va="center", color=INK)
bg.text(fx + 16, fy + 7.2, "집행액, 복구 면적, 사업 건수 (집행 증빙)", fontsize=T_BODY, va="center", color=INK)
bg.text(fx + 1.6, fy + 3.0, "기록되지 않는 것", fontsize=T_BODY, fontweight="bold", va="center", color=RED)
bg.text(fx + 16, fy + 3.0, "피해지가 실제로 회복되었는지,\n예산이 취약한 곳에 닿았는지", fontsize=T_BODY, va="center", color=RED, linespacing=1.3)
# 오른쪽: 예산 가로 막대
ax = sub_axes(fig, H, 76, 1.0, 22, 10.0)
items = [("기후대응기금 적응", 1654), ("특별교부세 폭염", 607.5), ("서울시 폭염 대책", 359.4), ("환경부 취약계층", 100), ("성과 검증 전용", 0)]
ys = np.arange(len(items))[::-1]
ax.barh(ys, [v for _, v in items], color=[POINT["navy"]] * 4 + [RED], height=0.6, edgecolor="none")
for yv, (k, v) in zip(ys, items):
    ax.text((v if v else 0) + 40, yv, ("0" if v == 0 else f"{v:,.0f}"), va="center", fontsize=T_SMALL, color=(RED if v == 0 else INK), fontweight=("bold" if v == 0 else "normal"))
ax.set_yticks(ys); ax.set_yticklabels([k for k, _ in items], fontsize=T_SMALL); ax.set_xlim(0, 2400); ax.set_xticks([])
for s_ in ("top", "right", "bottom"):
    ax.spines[s_].set_visible(False)
ax.tick_params(axis="y", length=0)
bg.text(60, fy + fh - 0.2, "(b)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(63.5, fy + fh - 0.2, "집행 예산과 성과 검증 예산(억 원, 2025~2026)", fontsize=T_HEAD, fontweight="bold", va="top")
save(fig, bg, "fig_story")

# ===================== 2. 서비스 구성도(가로형) =====================
fig, bg, H = canvas(2.55); bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
header(bg, 1, H - 4.0, 18, 3.4, "입력 자료"); header(bg, 22, H - 4.0, 53, 3.4, "검증 엔진"); header(bg, 78, H - 4.0, 21, 3.4, "산출물")
# 입력 3종(세로 스택)
ty = H - 11.2
para(bg, 1.5, ty, 15, 5.6, 1.6, PASTEL[2]); boxes_log.append((bg.text(1.5 + 8.3, ty + 2.8, "사업 대장\n위치, 기간, 예산", fontsize=T_SMALL, ha="center", va="center", linespacing=1.3, zorder=3), (1.5, ty, 16.6, 5.6)))
im = Image.open(RES / "fire-uiseong-2025/pre.png").convert("RGB"); im.thumbnail((700, 500)); arr = np.asarray(im)
sx, sy, sw, sh = 1.5, ty - 10.2, 15, 6.6; skew = sh * math.tan(math.radians(16))
for k in (2, 1):
    para(bg, sx + 0.8 * k, sy + 0.8 * k, sw, sh, skew, "white", ec="#8C8C8C", z=1)
tr = Affine2D().translate(-sx, -sy).skew_deg(16, 0).translate(sx, sy) + bg.transData
bg.imshow(arr, extent=(sx, sx + sw, sy, sy + sh), transform=tr, zorder=2, interpolation="antialiased", aspect="auto")
para(bg, sx, sy, sw, sh, skew, "none", ec=GREY_D, z=3)
bg.text(sx + sw / 2 + 0.8, sy - 1.0, "위성 아카이브\nSentinel-1/2, Landsat", fontsize=T_SMALL, ha="center", va="top", linespacing=1.25, color=GREY_D)
py = sy - 10.2
para(bg, 1.5, py, 15, 5.6, 1.6, PASTEL[1]); boxes_log.append((bg.text(1.5 + 8.3, py + 2.8, "수혜 대상 속성\n건축물대장, SGIS", fontsize=T_SMALL, ha="center", va="center", linespacing=1.3, zorder=3), (1.5, py, 16.6, 5.6)))
for yy in (ty + 2.8, sy + sh / 2, py + 2.8):
    bg.plot([18.2, 20.2], [yy, yy], color=INK, lw=0.9, zorder=4)
bg.plot([20.2, 20.2], [py + 2.8, ty + 2.8], color=INK, lw=0.9, zorder=4)
line(bg, [(20.2, sy + sh / 2), (22, sy + sh / 2)])
# 엔진 틀: 2×2 단계 + 남색 조립 블록
bw, bh, gx, gy = 24.5, 6.2, 1.6, 1.6
x1, x2 = 23.5, 23.5 + bw + gx
r1, r2 = H - 5.2 - gy - bh, H - 5.2 - 2 * gy - 2 * bh
frame(bg, 22, r2 - gy - 5.4 - 1.4, 53, (H - 4.6) - (r2 - gy - 5.4 - 1.4), "")
proc(bg, x1, r1, bw, bh, "1. 위성 지표 산출\n식생지수, 지표면온도, 침수 범위", fs=T_SMALL)
proc(bg, x2, r1, bw, bh, "2. 기준선과 대조구 설정\n같은 궤도, 같은 계절, 인접 구역", fs=T_SMALL)
bg.add_patch(patches.Rectangle((x1, r2), bw, bh, fc="white", ec=GREY_D, lw=0.7, zorder=2))
hl(bg, x1 + bw / 2, r2 + bh / 2, "3. 이중차분과 신뢰구간\n검출가능최소효과", fs=T_SMALL, ha="center")
proc(bg, x2, r2, bw, bh, "4. 형평성 감사\n노후도, 고령 비율, 집행 순위", fs=T_SMALL)
ny = r2 - gy - 5.4
proc(bg, x1, ny, 2 * bw + gx, 5.4, "성과 카드 조립\n출처 배지(실측, 계산, 규칙, 가정), 판정(검출, 미검출, 측정 불가)", fs=T_SMALL, fc=NAVY, ec=NAVY, tc="white", weight="bold")
line(bg, [(x1 + bw, r1 + bh / 2), (x2, r1 + bh / 2)])
line(bg, [(x2 + bw / 2, r1), (x2 + bw / 2, r2 + bh)])
line(bg, [(x2, r2 + bh / 2), (x1 + bw, r2 + bh / 2)])
line(bg, [(x1 + bw / 2, r2), (x1 + bw / 2, ny + 5.4)])
# 산출물
ox, ow = 79, 19
ry, rh = H - 22.6, 18.0
bg.add_patch(patches.FancyBboxPatch((ox, ry), ow, rh, boxstyle="round,pad=0,rounding_size=1.0", fc="white", ec=INK, lw=1.8, zorder=2))
ui = Image.open(OUT / "fig_ui_dashboard.png").convert("RGB").crop((1880, 160, 3160, 1990)); ui.thumbnail((520, 740))
axr = sub_axes(fig, H, ox + 1.0, ry + 0.9, ow - 2.0, rh - 4.4); axr.imshow(np.asarray(ui), interpolation="antialiased"); axr.axis("off")
bg.text(ox + ow / 2, ry + rh - 1.8, "성과 카드(영수증)", fontsize=T_BODY, fontweight="bold", color=RED, ha="center", va="center", zorder=5)
proc(bg, ox, 6.4, ow, 4.6, "이행점검 보고서 부록\n매년 4월 30일 제출", fs=T_SMALL)
proc(bg, ox, 1.2, ow, 4.6, "공시, 경영평가 첨부\n공공기관, 상장기업", fs=T_SMALL)
nc = ny + 2.7
bg.plot([x1 + 2 * bw + gx, 77], [nc, nc], color=INK, lw=0.9, zorder=4)
bg.plot([77, 77], [3.5, ry + rh / 2], color=INK, lw=0.9, zorder=4)
line(bg, [(77, ry + rh / 2), (ox, ry + rh / 2)]); line(bg, [(77, 8.7), (ox, 8.7)]); line(bg, [(77, 3.5), (ox, 3.5)])
save(fig, bg, "fig_service")

# ===================== 3. 이중차분 개념 + 재배분 순위 =====================
fig = plt.figure(figsize=(W, 2.55)); bg = fig.add_axes([0, 0, 1, 1]); bg.axis("off")
a1 = fig.add_axes([0.08, 0.19, 0.38, 0.66]); a2 = fig.add_axes([0.60, 0.19, 0.38, 0.66])
a1.plot([0, 1], [1.00, 0.72], color=POINT["crimson"], lw=2.0, marker="o", ms=5, label="처리구(사업 시행)")
a1.plot([0, 1], [1.00, 0.92], color=POINT["teal"], lw=2.0, marker="s", ms=5, ls="--", label="대조구(인접 미시행)")
a1.plot([1, 1], [0.72, 0.92], color=INK, lw=0.9); a1.plot([0.985, 1.015], [0.72, 0.72], color=INK, lw=0.9); a1.plot([0.985, 1.015], [0.92, 0.92], color=INK, lw=0.9)
a1.text(1.04, 0.82, "효과\n= 차이의 차이", fontsize=T_SMALL, va="center", color=INK, linespacing=1.25)
a1.text(0.5, 1.03, "계절, 기상, 전체 추세는 두 구역이 함께 겪음", fontsize=T_SMALL, ha="center", color=GREY_D)
a1.set_xlim(-0.12, 1.42); a1.set_ylim(0.6, 1.12); a1.set_xticks([0, 1]); a1.set_xticklabels(["사업 전", "사업 후"], fontsize=T_BODY); a1.set_yticks([])
a1.set_ylabel("위성 지표(온도, 식생, 침수)", fontsize=T_SMALL)
a1.legend(loc="lower left", frameon=False, fontsize=T_SMALL)
for s_ in ("top", "right"):
    a1.spines[s_].set_visible(False)
a1.text(-0.12, 1.20, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); a1.text(-0.02, 1.20, "처리구 대 대조구의 사업 전후 비교", fontsize=T_HEAD, fontweight="bold", va="top")
rows = [("809동", 11.42, "후보"), ("807동", 9.82, "후보"), ("808동", 8.57, "후보"), ("802동", 7.00, "후보"), ("805동", 6.55, "후보"), ("801동", 5.36, "시공"), ("803동", 5.03, "대조"), ("804동", 4.65, "시공"), ("806동", 4.65, "후보")]
col = {"후보": POINT["navy"], "시공": POINT["crimson"], "대조": POINT["grey"]}
a2.barh(range(len(rows))[::-1], [r[1] for r in rows], color=[col[r[2]] for r in rows], height=0.62, edgecolor="none")
a2.set_yticks(range(len(rows))[::-1]); a2.set_yticklabels([r[0] for r in rows], fontsize=T_SMALL)
for i, r in enumerate(rows):
    a2.text(r[1] + 0.15, len(rows) - 1 - i, f"{r[1]:.1f}", va="center", fontsize=T_SMALL, color=INK)
a2.set_xlim(0, 14); a2.set_xlabel("지붕 100 m²당 세대수", fontsize=T_SMALL); a2.tick_params(axis="x", labelsize=T_SMALL)
for s_ in ("top", "right"):
    a2.spines[s_].set_visible(False)
h_ = [patches.Patch(color=col[k], label=k) for k in ("후보", "시공", "대조")]
a2.legend(handles=h_, loc="lower right", frameon=False, fontsize=T_SMALL)
a2.text(-0.24, 1.10, "(b)", fontsize=T_HEAD, fontweight="bold", va="top", transform=a2.transAxes); a2.text(-0.10, 1.10, "가양8단지 9개 동의 다음 집행 순위", fontsize=T_HEAD, fontweight="bold", va="top", transform=a2.transAxes)
save(fig, bg, "fig_did")

# ===================== 4. 법정 달력(재채색) =====================
fig, ax = plt.subplots(figsize=(W, 2.5)); bg = ax
months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
ax.set_xlim(0.5, 12.5); ax.set_ylim(0, 5.3); ax.set_yticks([]); ax.set_xticks(range(1, 13)); ax.set_xticklabels(months, fontsize=T_SMALL)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
rows = [(4.35, "지자체 적응대책 이행점검(탄소중립기본법 제40조)", [(1, 4.0, POINT["navy"], "결과보고서 작성")], 4.0, "4월 30일 제출"),
        (3.25, "공공기관 적응대책 이행실적(제41조, 2026년 1월 지침)", [(1, 3.5, POINT["navy"], "이행실적 집계")], 3.5, "상반기 제출"),
        (2.15, "지자체 여름철 자연재난 대책(폭염 포함)", [(3, 5.0, POINT["ochre"], "대책 수립")], 5.0, "5월 전 확정"),
        (1.05, "위성 관측 가용 시기", [(5, 10.0, POINT["teal"], "생장기 식생, 호우 침수, 폭염기 지표면온도")], None, None)]
for y, label, bars, due, duetxt in rows:
    ax.text(0.55, y + 0.52, label, fontsize=T_SMALL, color=INK, va="bottom")
    for x0, x1_, c, t in bars:
        ax.barh(y, x1_ - x0, left=x0, height=0.42, color=c, alpha=0.9); ax.text((x0 + x1_) / 2, y, t, ha="center", va="center", fontsize=T_SMALL, color="white", fontweight="bold")
    if due:
        ax.plot([due, due], [y - 0.3, y + 0.3], color=RED, lw=2); ax.text(due + 0.1, y - 0.02, duetxt, fontsize=T_SMALL, color=RED, va="center")
ax.axvspan(1, 3.0, color=PASTEL[0], alpha=0.6, zorder=0); ax.text(2.0, 0.28, "납품 창구: 1월부터 3월(전년 관측 집계)", ha="center", fontsize=T_SMALL, color=BLUE, fontweight="bold")
save(fig, bg, "fig_calendar")

# ===================== 5. 시제품 화면 잘라내기(가로 2:1) =====================
ui_full = Image.open(OUT / "fig_ui_dashboard.png").convert("RGB")
ui_full.crop((0, 0, 3200, 1600)).save(OUT / "fig_ui_crop.png")

for stem, kind, hits in report:
    print(stem, kind, len(hits), hits[:6])
