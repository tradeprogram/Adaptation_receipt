# -*- coding: utf-8 -*-
"""최종 심사 기획서 그림 — mechanical-pen-figures §7·§8(가로 6.8 in, 글자 9.0/8.0/7.2 pt, 직각 꺾은선, 형광펜 1~2곳, 실제 자료 썸네일).

fig_overview.png     : 한 장 요약(문제, 해법, 효용)
fig_gap.png          : 적응 정책 순환과 효과 확인 단계의 공백
fig_market.png       : 법정 보고 의무 주체로 정의한 시장 구조
fig_architecture.png : 시스템 구성도(자료 수집, 검증 계산, 서비스 서버, 화면) — 사용자 첨부 계층형 구성도 형태
fig_asis_tobe.png    : 적응대책 담당자의 1년, 현행 대 도입 후
fig_exposure.png     : 의성·안동 산불 피해와 읍면 고령화지수
fig_flood.png        : 부여 일대 정비 전후 침수 비교와 강우 보정
fig_roadmap.png      : 확장 계획(사업 유형, 고객, 지역)
fig_benefit.png      : 성과 카드 한 장이 주체별로 만드는 효용
저장 전 글자 겹침 전수 검사와 글자가 상자 밖으로 나갔는지 검사를 통과해야 한다(report 출력이 모두 빈 목록).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.transforms import Bbox
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "figures"; RES = ROOT / "app/cache/results"; SHOT = OUT / "shots"
plt.rcParams.update({"font.family": ["Arial", "Malgun Gothic"], "axes.unicode_minus": False})
W = 6.8; T_HEAD, T_BODY, T_SMALL = 9.0, 8.0, 7.2
INK, GREY_D, GREY_F, GREY_H, GREY_M = "#1F1F1F", "#404040", "#F2F2F2", "#D9D9D9", "#595959"
NAVY, RED, BLUE, HL = "#1F3864", "#C00000", "#2F5597", "#FFE45C"
PASTEL = ["#DCE6F2", "#E2EFD9", "#FFF2CC", "#FBE5D6", "#E4DFEC", "#DDEBF7"]
POINT = {"navy": "#1F3A5F", "crimson": "#B4232C", "ochre": "#B8860B", "teal": "#1E7F86", "plum": "#6B4C8A", "grey": "#8C8C8C"}

boxes_log = []
canvas = lambda h_in: (lambda fig: (fig, fig.add_axes([0, 0, 1, 1]), 100 * h_in / W))(plt.figure(figsize=(W, h_in)))
sub_axes = lambda fig, H, x, y, w, h: fig.add_axes([x / 100, y / H, w / 100, h / H])
frame = lambda bg, x, y, w, h, title=None, ec="#7F7F7F", fc=GREY_F, ls="-": (bg.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=0.8, ls=ls, zorder=0)), bg.text(x + 1.2, y + h - 0.9, title, fontsize=T_HEAD, fontweight="bold", style="italic", color=INK, va="top") if title else None)
proc = lambda bg, x, y, w, h, text, fs=T_BODY, fc="white", ec=GREY_D, tc=INK, weight="normal", lw=0.7: (bg.add_patch(patches.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=2)), boxes_log.append((bg.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center", color=tc, fontweight=weight, linespacing=1.3, zorder=3), (x, y, w, h))))
header = lambda bg, x, y, w, h, text, fs=T_HEAD: (bg.add_patch(patches.Rectangle((x, y), w, h, fc=GREY_H, ec=GREY_D, lw=0.7, zorder=2)), boxes_log.append((bg.text(x + w / 2, y + h / 2, text, fontsize=fs, fontweight="bold", ha="center", va="center", color=INK, zorder=3, linespacing=1.25), (x, y, w, h))))
vband = lambda bg, x, y, w, h, text: (bg.add_patch(patches.Rectangle((x, y), w, h, fc=GREY_H, ec="none", zorder=1)), bg.text(x + w / 2, y + h / 2, text, fontsize=T_HEAD, fontweight="bold", ha="center", va="center", rotation=90, color=INK, zorder=3, linespacing=1.2))
hl = lambda bg, x, y, text, fs=T_BODY, ha="left": bg.text(x, y, text, fontsize=fs, fontweight="bold", color=INK, ha=ha, va="center", zorder=6, linespacing=1.3, bbox=dict(boxstyle="square,pad=0.18", fc=HL, ec="none"))
line = lambda bg, pts, color=INK, lw=0.9, arrow=True, ls="-": (bg.plot([p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]], color=color, lw=lw, ls=ls, solid_capstyle="butt", zorder=4), bg.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0), zorder=4)) if arrow else bg.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, ls=ls, zorder=4)
block = lambda bg, x, y0, y1, w=3.0, fc="#A6A6A6": bg.add_patch(patches.FancyArrow(x, y0, 0, y1 - y0, width=w, head_width=w * 1.9, head_length=1.6, length_includes_head=True, fc=fc, ec="none", zorder=1))
hblock = lambda bg, x0, x1, y, w=3.0, fc="#A6A6A6": bg.add_patch(patches.FancyArrow(x0, y, x1 - x0, 0, width=w, head_width=w * 1.9, head_length=1.6, length_includes_head=True, fc=fc, ec="none", zorder=1))
img_ax = lambda fig, H, x, y, w, h, arr, border=GREY_D: (lambda a: (a.imshow(arr, aspect="auto", interpolation="lanczos"), a.set_xticks([]), a.set_yticks([]), [s.set_edgecolor(border) for s in a.spines.values()], [s.set_linewidth(0.7) for s in a.spines.values()]))(sub_axes(fig, H, x, y, w, h))
on_white = lambda p: (lambda im: np.asarray(Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("RGB")))(Image.open(p).convert("RGBA"))
over = lambda base, top, a=1.0: (lambda b, t: np.asarray(Image.alpha_composite(b, Image.fromarray((np.asarray(t).astype(float) * [1, 1, 1, a]).astype("uint8"), "RGBA")).convert("RGB")))(Image.open(base).convert("RGBA"), Image.open(top).convert("RGBA").resize(Image.open(base).size))

report = []
texts_of = lambda fig: [t for ax in fig.axes for t in list(ax.texts) + [ax.title] + ((list(ax.get_xticklabels()) + list(ax.get_yticklabels())) if ax.axison else []) + (list(ax.get_legend().get_texts()) if ax.get_legend() is not None else []) if t.get_visible() and t.get_text().strip()]
bbx = lambda t, r: t.get_window_extent(renderer=r).shrunk(0.94, 0.80)
overlaps = lambda fig, r: (lambda L: [(a.get_text().replace("\n", " ")[:24], b.get_text().replace("\n", " ")[:24]) for i, a in enumerate(L) for b in L[i + 1:] if bbx(a, r).overlaps(bbx(b, r))])(texts_of(fig))
boxpx = lambda bg, x, y, w, h: Bbox.from_extents(*bg.transData.transform((x, y)), *bg.transData.transform((x + w, y + h)))
outside = lambda fig, bg, r: [t.get_text().replace("\n", " ")[:24] for t, (x, y, w, h) in boxes_log if t.figure is fig and not (boxpx(bg, x, y, w, h).contains(*t.get_window_extent(renderer=r).min) and boxpx(bg, x, y, w, h).contains(*t.get_window_extent(renderer=r).max))]
dots = lambda fig: [t.get_text()[:20] for t in texts_of(fig) if "·" in t.get_text() or "—" in t.get_text()]
check = lambda fig, bg, stem: (fig.canvas.draw(), report.append((stem, "겹침", overlaps(fig, fig.canvas.get_renderer()))), report.append((stem, "상자밖", outside(fig, bg, fig.canvas.get_renderer()))), report.append((stem, "가운뎃점", dots(fig))))
save = lambda fig, bg, stem: (check(fig, bg, stem), fig.savefig(OUT / f"{stem}.png", dpi=280, bbox_inches="tight", pad_inches=0.04, facecolor="white"), plt.close(fig))
setup = lambda h_in: (lambda t: (t[1].set_xlim(0, 100), t[1].set_ylim(0, t[2]), t[1].axis("off"), t)[-1])(canvas(h_in))

fire = json.loads((RES / "fire-uiseong-2025/fire.json").read_text(encoding="utf-8"))
heat = json.loads((RES / "heat-gayang8-coolroof/heat.json").read_text(encoding="utf-8"))
flood = json.loads((RES / "flood-buyeo-drainage/flood.json").read_text(encoding="utf-8"))
exf = json.loads((RES / "fire-uiseong-2025/exposure.json").read_text(encoding="utf-8"))
exw = json.loads((RES / "flood-buyeo-drainage/exposure.json").read_text(encoding="utf-8"))
gjf = json.loads((RES / "fire-uiseong-2025/exposure_areas.geojson").read_text(encoding="utf-8"))
gjw = json.loads((RES / "flood-buyeo-drainage/exposure_areas.geojson").read_text(encoding="utf-8"))
mv = lambda r, k: r["metrics"][k]["value"]
AG = ["#f6f1e4", "#e9cf9c", "#cf9a5a", "#9a6421", "#5a3412"]
ag_cmap = matplotlib.colors.LinearSegmentedColormap.from_list("ag", AG)
rings = lambda g: ([g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]])

# ===================== 1. 한 장 요약 =====================
fig, bg, H = setup(3.05)
cols = [(2, "문제", "집행은 기록되고\n효과는 기록되지 않는 적응 예산"), (35, "해법", "공개 위성 아카이브로 사업마다\n효과와 형평성을 사후 검증"), (68, "효용", "다음 예산을 효과와\n취약성 근거로 배분")]
for x, t, s in cols:
    header(bg, x, H - 6.2, 30, 4.6, t)
    bg.text(x + 15, H - 8.6, s, fontsize=T_SMALL, ha="center", va="top", color=GREY_M, linespacing=1.25, wrap=False)
for x0 in (32.2, 65.2):
    hblock(bg, x0, x0 + 2.6, H - 3.9, w=2.0)
# 문제 열: 예산 막대
ax = sub_axes(fig, H, 8.5, 10, 22, 17.5)
items = [("기후대응기금 적응", 1654), ("특별교부세 폭염", 607.5), ("서울시 폭염 대책", 359.4), ("성과 검증 전용", 0)]
ys = np.arange(len(items))[::-1]
ax.barh(ys, [v for _, v in items], color=[POINT["navy"]] * 3 + [RED], height=0.58)
for yv, (k, v) in zip(ys, items):
    ax.text(v + 45, yv, "0" if v == 0 else f"{v:,.0f}", va="center", fontsize=T_SMALL, color=RED if v == 0 else INK, fontweight="bold" if v == 0 else "normal")
ax.set_yticks(ys); ax.set_yticklabels([k for k, _ in items], fontsize=T_SMALL); ax.set_xlim(0, 2300); ax.set_xticks([])
[ax.spines[s].set_visible(False) for s in ("top", "right", "bottom")]; ax.tick_params(axis="y", length=0)
bg.text(17, 7.4, "적응 집행 예산(억 원, 2025~2026)", fontsize=T_SMALL, ha="center", color=GREY_M)
bg.text(17, 3.2, "산불 피해 104,004 ha, 복구계획 1조 8,809억 원\n당해 복구 실적 1 ha(2025 국정감사)", fontsize=T_SMALL, ha="center", va="center", color=INK, linespacing=1.3)
# 해법 열: 실제 위성 썸네일 3장 + 카드
thumbs = [over(RES / "fire-uiseong-2025/post.png", RES / "fire-uiseong-2025/dnbr.png", 0.85), on_white(RES / "heat-gayang8-coolroof/lst_before.png"), on_white(RES / "flood-buyeo-drainage/flood_change.png")]
names = ["산불 회복", "옥상 차열", "배수 정비"]
for i, (arr, nm) in enumerate(zip(thumbs, names)):
    img_ax(fig, H, 36 + i * 9.7, 18.0, 8.6, 9.0, arr)
    bg.text(36 + i * 9.7 + 4.3, 17.0, nm, fontsize=T_SMALL, ha="center", va="top", color=INK)
line(bg, [(50, 13.6), (50, 11.8)])
bg.add_patch(patches.FancyBboxPatch((38.5, 2.2), 23, 9.4, boxstyle="round,pad=0,rounding_size=0.8", fc="white", ec=INK, lw=1.8, zorder=2))
bg.text(50, 9.3, "성과 카드", fontsize=T_HEAD, fontweight="bold", color=RED, ha="center", va="center", zorder=3)
bg.text(50, 5.0, "판정, 효과 크기, 오차 범위\n형평성, 조치 사항, 한계", fontsize=T_SMALL, ha="center", va="center", color=INK, linespacing=1.3, zorder=3)
# 효용 열
ben = [("담당 부서", "이행점검 보고서 부록"), ("예산 부서", "효과 기준 재배분"), ("주민, 취약계층", "공개 카드로 확인"), ("중앙정부, 의회", "지자체 간 비교")]
for i, (who, what) in enumerate(ben):
    yy = 22.3 - i * 5.6
    proc(bg, 69, yy, 12.5, 4.8, who, fs=T_SMALL, weight="bold")
    proc(bg, 82.5, yy, 15.5, 4.8, what, fs=T_SMALL, fc="#F7F7F7")
save(fig, bg, "fig_overview")

# ===================== 2. 적응 정책 순환과 공백 =====================
fig, bg, H = setup(3.1)
bg.text(1, H - 1, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(4.5, H - 1, "법정 적응대책의 연간 순환과 비어 있는 단계", fontsize=T_HEAD, fontweight="bold", va="top")
stages = [("위험 평가", "VESTAP, 기후변화\n상황지도, 열환경 지도"), ("대책 수립", "5년 주기 수립 용역\n5,000~6,970만 원"), ("사업 집행", "복구, 쿨루프,\n배수 정비"), ("효과 확인", "공식 단계 없음"), ("이행점검 보고", "매년 4월 30일\n집행액, 건수"), ("예산 배분", "전년 실적,\n민원 기준")]
cx, cy, R = 30, H / 2 - 3, 13.5
ang = np.radians(np.linspace(90, 90 - 300, 6))
pos = [(cx + R * 1.55 * np.cos(a), cy + R * np.sin(a)) for a in ang]
bw, bh = 15, 5.2
for i, ((t, s), (x, y)) in enumerate(zip(stages, pos)):
    gap = t == "효과 확인"
    bg.add_patch(patches.Rectangle((x - bw / 2, y - bh / 2), bw, bh, fc="white" if not gap else "#FBE5D6", ec=RED if gap else GREY_D, lw=1.6 if gap else 0.7, ls="--" if gap else "-", zorder=2))
    boxes_log.append((bg.text(x, y, t, fontsize=T_BODY, fontweight="bold", ha="center", va="center", color=RED if gap else INK, zorder=3), (x - bw / 2, y - bh / 2, bw, bh)))
# 순환 화살표(호)
for i in range(6):
    a0, a1 = ang[i] - np.radians(14), ang[(i + 1) % 6] + np.radians(14)
    if a1 > a0: a1 -= 2 * np.pi
    t_ = np.linspace(a0, a1, 30)
    xs, ys_ = cx + R * 1.55 * np.cos(t_) * 0.78, cy + R * np.sin(t_) * 0.78
    bg.plot(xs[:-1], ys_[:-1], color=GREY_M, lw=0.9, zorder=1)
    bg.annotate("", xy=(xs[-1], ys_[-1]), xytext=(xs[-2], ys_[-2]), arrowprops=dict(arrowstyle="-|>,head_length=0.4,head_width=0.2", color=GREY_M, lw=0.9), zorder=1)
bg.text(cx, cy, "매년\n반복", fontsize=T_BODY, ha="center", va="center", color=GREY_M, linespacing=1.3)
# 오른쪽 (b): 단계별 기존 도구와 적응 영수증
bg.text(60, H - 1, "(b)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(63.5, H - 1, "단계별로 쓰이는 근거", fontsize=T_HEAD, fontweight="bold", va="top")
rows_b = [("위험 평가", "격자 취약성 지도(무료)", False), ("대책 수립", "수립 용역의 정성 서술", False), ("사업 집행", "집행 대장, 정산 서류", False), ("효과 확인", "적응 영수증 성과 카드", True), ("이행점검 보고", "카드를 부록으로 첨부", True), ("예산 배분", "효과와 취약성 기준 순위", True)]
for i, (st, ev, ours) in enumerate(rows_b):
    yy = H - 9.5 - i * 6.1
    proc(bg, 60, yy, 13, 4.9, st, fs=T_SMALL, weight="bold", fc=GREY_F)
    proc(bg, 74, yy, 24, 4.9, ev, fs=T_SMALL, ec=RED if ours else GREY_D, tc=RED if ours and st == "효과 확인" else INK, weight="bold" if ours else "normal", lw=1.3 if ours else 0.7)
save(fig, bg, "fig_gap")

# ===================== 3. 시장 구조 =====================
fig, bg, H = setup(2.7)
bg.text(1, H - 1, "법정 보고 의무 주체로 정의한 시장(2025~2027)", fontsize=T_HEAD, fontweight="bold", va="top")
mk = [("기초, 광역 지자체", 243, "매년 4월 30일 이행점검", "탄소중립기본법 제40조", NAVY),
      ("제3차 적응대책 발주", 150, "2025~2027 수립 용역", "건당 5,000~6,970만 원", POINT["teal"]),
      ("공공기관", 62, "적응대책 수립, 이행 지침", "2026-01 정량 평가 검토", POINT["ochre"]),
      ("상장사 지속가능성 공시", 291, "FY2027부터 단계 적용", "물리적 위험 공시 10/99곳", POINT["plum"])]
ax = sub_axes(fig, H, 24, 4, 34, 28)
ys = np.arange(4)[::-1]
ax.barh(ys, [m[1] for m in mk], color=[m[4] for m in mk], height=0.55)
for yv, m in zip(ys, mk):
    ax.text(m[1] + 6, yv, f"{m[1]}", va="center", fontsize=T_BODY, fontweight="bold", color=INK)
ax.set_yticks(ys); ax.set_yticklabels([m[0] for m in mk], fontsize=T_SMALL); ax.set_xlim(0, 340); ax.set_xticks([])
[ax.spines[s].set_visible(False) for s in ("top", "right", "bottom")]; ax.tick_params(axis="y", length=0)
for i, m in enumerate(mk):
    yy = 4 + (3 - i) * 7.0 + 0.7
    proc(bg, 62, yy, 18, 5.6, m[2], fs=T_SMALL)
    proc(bg, 80.5, yy, 17.5, 5.6, m[3], fs=T_SMALL, fc="#F7F7F7")
bg.text(80, H - 1, "구매 근거와 단가", fontsize=T_SMALL, ha="center", va="top", color=GREY_M)
bg.text(41, 1.5, "주체 수(곳)", fontsize=T_SMALL, ha="center", color=GREY_M)
save(fig, bg, "fig_market")

LOGO = OUT / "logos"
logo_arr = lambda key: (lambda im: (lambda a: a.crop(Image.fromarray(((np.asarray(a)[:, :, 3] > 20) & (np.asarray(a)[:, :, :3].min(axis=2) < 245)).astype("uint8") * 255).getbbox()))(im))(Image.open(LOGO / f"{key}.png").convert("RGBA"))
logo_px = lambda key, h, bgc: (lambda im: (lambda px: Image.alpha_composite(Image.new("RGBA", im.size, bgc), im).convert("RGB").resize((max(1, round(px * im.size[0] / im.size[1])), px), Image.LANCZOS))(max(1, round(h * W / 100 * 280))))(logo_arr(key))
logo = lambda fig, H, key, x, y, h, cy=False, bgc="#FFFFFF": (lambda im: (lambda w: ((lambda a: (a.imshow(np.asarray(im), interpolation="none"), a.axis("off")))(fig.add_axes([x / 100, (y - (h / 2 if cy else 0)) / H, w / 100, h / H])), x + w)[1])(h * im.size[0] / im.size[1]))(logo_px(key, h, bgc))
# ===================== 4. 시스템 구성도 =====================
fig, bg, H = setup(9.0)
LX, X0, X1 = 2, 9.5, 98
bands = [("자료 수집\n공공 API, 위성", H - 30.5, 29.5), ("검증 계산\n로컬 연구 PC", H - 64.5, 31.5), ("서비스 서버\nVercel 서버리스", H - 90.5, 23.5), ("화면\n웹 브라우저", 1.0, H - 93.5)]
for t, y, h in bands:
    frame(bg, LX, y, X1 - LX, h)
    vband(bg, LX, y, 6.5, h, t)
# (1) 자료 타일 2줄 × 5
tiles = [(["kma"], "API허브 ASOS", "시간강우, 호우 사건", ""), (["mois"], "재난안전데이터", "무더위쉼터", ""), (["mods"], "SGIS", "읍면 인구, 경계", ""), (["molit"], "공공데이터포털", "건축물대장 표제부", ""), (["molit"], "브이월드", "건물 외곽선", ""),
         (["esa", "copernicus"], "Sentinel-1", "레이더 침수 범위", ""), (["esa", "copernicus"], "Sentinel-2", "산불 피해, 회복", ""), (["usgs"], "Landsat 8/9", "지표면온도", ""), (["microsoft"], "Planetary Computer", "위성 검색, 읽기", ""), (["kfs"], "사업 대장", "위치, 기간, 예산", "지자체")]
LH = {"kma": 3.0, "mois": 3.0, "mods": 3.0, "molit": 3.0, "kfs": 3.0, "esa": 2.7, "copernicus": 2.5, "usgs": 2.6, "microsoft": 2.1}
tw, th, tg = 16.6, 12.2, 0.8
for i, (keys, prod, use, extra) in enumerate(tiles):
    r_, c_ = divmod(i, 5); x = X0 + 1.2 + c_ * (tw + tg); y = H - 15.5 - r_ * (th + 1.3)
    bg.add_patch(patches.Rectangle((x, y), tw, th, fc="white", ec=GREY_D, lw=0.7, zorder=2))
    lx = x + 1.0
    for k in keys:
        lx = logo(fig, H, k, lx, y + th - 2.5, LH[k], cy=True) + 0.8
    if extra:
        boxes_log.append((bg.text(lx + 0.2, y + th - 2.5, extra, fontsize=T_SMALL, fontweight="bold", va="center", color=INK, zorder=3), (x, y, tw, th)))
    boxes_log.append((bg.text(x + tw / 2, y + th / 2 - 0.6, prod, fontsize=T_BODY, fontweight="bold", ha="center", va="center", color=INK, zorder=3), (x, y, tw, th)))
    boxes_log.append((bg.text(x + tw / 2, y + 2.0, use, fontsize=T_SMALL, ha="center", va="center", color=GREY_M, zorder=3), (x, y, tw, th)))
block(bg, 50, H - 30.3, H - 34.6, w=3.2)
# (2) 검증 모듈 4개: 실제 산출물 썸네일
mods = [("산불 회복 추적", over(RES / "fire-uiseong-2025/post.png", RES / "fire-uiseong-2025/dnbr.png", 0.85), f"피해 {exf['hazard_ha']:,.0f} ha\nSentinel-2 장면 5"),
        ("옥상 차열 검정", on_white(RES / "heat-gayang8-coolroof/lst_before.png"), f"Landsat 장면 {mv(heat, 'scenes_used')}\n최소 변화 {mv(heat, 'mde_c'):.2f}℃"),
        ("배수 정비 침수 비교", on_white(RES / "flood-buyeo-drainage/flood_change.png"), f"호우 {len(flood['events'])}건\n레이더 관측 A/B {sum(1 for e in flood['events'] if e['grade'] in 'AB')}건"),
        ("취약 지역 노출", None, f"읍면 {exf['n_areas'] + exw['n_areas']}곳\nSGIS 고령화지수")]
mw, mh = 16.4, 15.0
for i, (nm, arr, cap) in enumerate(mods):
    x = X0 + 1.2 + i * (mw + 1.4); y = H - 58.5
    header(bg, x, y + mh + 0.8, mw, 4.0, nm, fs=T_SMALL)
    if arr is not None:
        img_ax(fig, H, x, y, mw, mh, arr)
    else:
        a = sub_axes(fig, H, x, y, mw, mh)
        for f in gjf["features"]:
            v = f["properties"]["aged_idx"] or 0
            for rg in rings(f["geometry"]):
                a.add_patch(patches.Polygon(rg, closed=True, fc=ag_cmap(min(1, max(0, (v - 300) / 2200))), ec="white", lw=0.4))
        a.set_xlim(128.45, 128.95); a.set_ylim(36.26, 36.55); a.set_aspect(1 / np.cos(np.radians(36.4))); a.set_xticks([]); a.set_yticks([])
        [s.set_edgecolor(GREY_D) for s in a.spines.values()]; [s.set_linewidth(0.7) for s in a.spines.values()]
    bg.text(x + mw / 2, y - 1.0, cap, fontsize=T_SMALL, ha="center", va="top", color=INK, linespacing=1.25)
gx, gy, gw_, gh_ = X0 + 1.2 + 4 * (mw + 1.4), H - 52, 13.9, 15
bg.add_patch(patches.Rectangle((gx, gy), gw_, gh_, fc="white", ec=GREY_D, lw=0.7, zorder=2))
logo(fig, H, "github", gx + 2.6, gy + gh_ - 3.3, 3.2, cy=True)
boxes_log.append((bg.text(gx + 6.6, gy + gh_ - 3.3, "GitHub", fontsize=T_BODY, fontweight="bold", ha="left", va="center", zorder=3), (gx, gy, gw_, gh_)))
boxes_log.append((bg.text(gx + gw_ / 2, gy + 6.2, "공개 저장소\n코드, 결과 파일\n처리 매니페스트", fontsize=T_SMALL, ha="center", va="center", color=GREY_M, linespacing=1.3, zorder=3), (gx, gy, gw_, gh_)))
line(bg, [(X0 + 1.2 + 3 * (mw + 1.4) + mw + 0.3, H - 50.5), (gx, H - 50.5)])
bg.text(gx + gw_ / 2, gy - 1.2, "매년 1회 검정 후\n결과 반영", fontsize=T_SMALL, ha="center", va="top", color=GREY_M, linespacing=1.25)
block(bg, 50, H - 64.3, H - 68.6, w=3.2)
# (3) 서버
sx, sy, sw, sh = 33, H - 87.8, 34, 17.8
bg.add_patch(patches.Rectangle((sx, sy), sw, sh, fc=NAVY, ec=NAVY, zorder=2))
bg.add_patch(patches.FancyBboxPatch((sx + 6.5, sy + sh - 5.2), sw - 13, 4.0, boxstyle="round,pad=0,rounding_size=0.8", fc="white", ec="none", zorder=3))
logo(fig, H, "fastapi", sx + 8.0, sy + sh - 3.2, 2.6, cy=True)
bg.text(sx + sw - 7.6, sy + sh - 3.2, "서버", fontsize=T_HEAD, fontweight="bold", ha="right", va="center", color=NAVY, zorder=4)
boxes_log.append((bg.text(sx + sw / 2, sy + 6.6, "성과 카드    지도 화소 조회\n형평성 감사    취약 지역 노출\n설명 대화    보고 일정", fontsize=T_SMALL, ha="center", va="center", color="white", linespacing=1.6, zorder=3), (sx, sy, sw, sh)))
vx, vw = gx - 4.0, gw_ + 4.0
proc(bg, vx, H - 84.5, vw, 11.0, "\nGitHub 연동 자동 배포\n읽기 전용 운영", fs=T_SMALL)
logo(fig, H, "vercel", vx + vw / 2 - 4.6, H - 84.5 + 8.4, 2.0, cy=True)
line(bg, [(vx - 0.2, H - 79), (sx + sw + 0.2, H - 79)])
ext = [("gemini", "API, 카드 수치만 인용"), ("mods", "SGIS, 형평성 조회")]
for i, (a_, b_) in enumerate(ext):
    yy = H - 76.0 - i * 9.4
    bg.add_patch(patches.Rectangle((X0 + 1.2, yy), 19.0, 7.6, fc="white", ec=GREY_D, lw=0.7, zorder=2))
    lh_ = 2.3 if a_ == "gemini" else 2.6
    logo(fig, H, a_, X0 + 1.2 + 9.5 - lh_ * logo_arr(a_).size[0] / logo_arr(a_).size[1] / 2, yy + 5.3, lh_, cy=True)
    boxes_log.append((bg.text(X0 + 1.2 + 9.5, yy + 1.9, b_, fontsize=T_SMALL, ha="center", va="center", color=INK, zorder=3), (X0 + 1.2, yy, 19.0, 7.6)))
    line(bg, [(sx - 0.2, yy + 3.8), (X0 + 1.2 + 19.0 + 0.2, yy + 3.8)])
# GitHub → Vercel 점선(자동 배포)
line(bg, [(gx + gw_ / 2, gy - 5.8), (gx + gw_ / 2, H - 73.4)], color=GREY_M, lw=0.9, ls=(0, (3, 2)))
block(bg, 50, H - 90.4, H - 94.6, w=3.2)
# (4) 화면
bg.add_patch(patches.Rectangle((X0 + 1.2, 25.5), 19.5, 8.0, fc="white", ec=GREY_D, lw=0.7, zorder=2))
logo(fig, H, "maplibre", X0 + 2.4, 29.5, 4.4, cy=True)
boxes_log.append((bg.text(X0 + 7.6, 29.5, "MapLibre\n3D 지도, 지형,\n위성, 건물", fontsize=T_SMALL, ha="left", va="center", color=INK, linespacing=1.25, zorder=3), (X0 + 1.2, 25.5, 19.5, 8.0)))
bg.add_patch(patches.Rectangle((X0 + 1.2, 14.0), 19.5, 8.0, fc="#F7F7F7", ec=GREY_D, lw=0.7, zorder=2))
logo(fig, H, "aws", X0 + 2.4, 18.0, 3.0, cy=True, bgc="#F7F7F7")
boxes_log.append((bg.text(X0 + 8.3, 18.0, "지형 타일\nEsri 위성,\nOpenFreeMap", fontsize=T_SMALL, ha="left", va="center", color=INK, linespacing=1.25, zorder=3), (X0 + 1.2, 14.0, 19.5, 8.0)))
line(bg, [(X0 + 11, 22.2), (X0 + 11, 25.4)])
outs = [("성과 카드", "담당자 화면"), ("관할 요약", "과장, 의회 화면"), ("보고서 부록", "인쇄용 카드")]
for i, (a_, b_) in enumerate(outs):
    yy = 26.5 - i * 10.0
    bg.add_patch(patches.Rectangle((33, yy), 17, 8.0, fc="white", ec=INK if i == 0 else GREY_D, lw=1.6 if i == 0 else 0.7, zorder=2))
    boxes_log.append((bg.text(41.5, yy + 5.2, a_, fontsize=T_BODY, fontweight="bold", ha="center", va="center", color=RED if i == 0 else INK, zorder=3), (33, yy, 17, 8)))
    boxes_log.append((bg.text(41.5, yy + 2.2, b_, fontsize=T_SMALL, ha="center", va="center", color=GREY_M, zorder=3), (33, yy, 17, 8)))
line(bg, [(X0 + 1.2 + 19.5 + 0.2, 29.5), (33, 29.5)])
shot = SHOT / "ui_heat.png"
if shot.exists():
    im = Image.open(shot).convert("RGB"); w0, h0 = im.size
    iw = 44.5; ih = iw * h0 / w0
    img_ax(fig, H, 52.8, 4.0, iw, ih, np.asarray(im), border=INK)
    bg.text(52.8 + iw / 2, 4.0 + ih + 0.8, "시제품 화면(서울 가양8단지 쿨루프, 3D)", fontsize=T_SMALL, ha="center", va="bottom", color=GREY_M)
save(fig, bg, "fig_architecture")

# ===================== 5. 담당자의 1년 =====================
fig, bg, H = setup(2.9)
bg.text(1, H - 1, "적응대책 담당자의 1년", fontsize=T_HEAD, fontweight="bold", va="top")
mx0, mx1 = 16, 98; mon = lambda m: mx0 + (mx1 - mx0) * (m - 1) / 12
for m in range(1, 13):
    bg.text(mon(m) + (mx1 - mx0) / 24, H - 6.5, f"{m}월", fontsize=T_SMALL, ha="center", color=GREY_M)
    bg.plot([mon(m), mon(m)], [3, H - 8], color="#E6E6E6", lw=0.5, zorder=0)
lanes = [("현행", H - 18.5, [(1, 3, "사업 정산", "#F2F2F2"), (3, 4.9, "집행액, 건수\n집계", "#F2F2F2"), (4.9, 5.0, "", RED), (5.2, 8, "다음 해 사업 계획\n전년 실적, 민원 기준", "#F2F2F2"), (8, 12.9, "사업 집행, 효과 확인 없음", "#FBE5D6")]),
         ("도입 후", H - 33.5, [(1, 3.5, "위성 검정, 카드 조립\n(적응 영수증)", "#DCE6F2"), (3.5, 4.9, "카드를\n부록 첨부", "#E2EFD9"), (4.9, 5.0, "", RED), (5.2, 8, "카드의 조치 사항과\n집행 순위로 재배분", "#E2EFD9"), (8, 11, "사업 집행", "#F2F2F2"), (11, 12.9, "사업 대장\n전달", "#DCE6F2")])]
for nm, y, segs in lanes:
    header(bg, 2, y, 12.5, 9.5, nm)
    for a_, b_, t, c in segs:
        if not t:
            bg.plot([mon(a_) + 1.2, mon(a_) + 1.2], [y - 1.0, y + 10.5], color=RED, lw=1.4, zorder=4); continue
        proc(bg, mon(a_), y, mon(b_) - mon(a_) - 0.4, 9.5, t, fs=T_SMALL, fc=c)
bg.text(mon(4.9) + 2.0, H - 1.0, "4.30 이행점검 제출", fontsize=T_SMALL, color=RED, fontweight="bold", ha="left", va="top")
bg.plot([mon(4.9) + 1.2, mon(4.9) + 1.2], [H - 3.6, H - 8.4], color=RED, lw=1.0, zorder=4)
proc(bg, 16, 2.0, 82, 6.0, "담당자가 준비하는 것은 사업 대장 한 장, 결정 권한은 현행과 같이 담당 기관", fs=T_SMALL, fc="#F7F7F7", ec="#BFBFBF")
save(fig, bg, "fig_asis_tobe")

# ===================== 6. 취약 지역 노출(의성·안동) =====================
fig = plt.figure(figsize=(W, 3.0)); bg = fig.add_axes([0, 0, 1, 1]); H = 100 * 3.0 / W; bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
a = sub_axes(fig, H, 2, 2, 56, H - 6)
for f in gjf["features"]:
    v = f["properties"]["aged_idx"] or 0
    for rg in rings(f["geometry"]):
        a.add_patch(patches.Polygon(rg, closed=True, fc=ag_cmap(min(1, max(0, (v - 300) / 2200))), ec="white", lw=0.5, zorder=1))
dn = Image.open(RES / "fire-uiseong-2025/dnbr.png").convert("RGBA"); dna = np.asarray(dn).copy(); m = dna[..., 3] > 0
dna[m] = [25, 25, 25, 120]
a.imshow(dna, extent=(128.45, 128.95, 36.26, 36.55), zorder=2, interpolation="nearest")
a.set_xlim(128.45, 128.95); a.set_ylim(36.26, 36.55); a.set_aspect(1 / np.cos(np.radians(36.4)))
a.set_xticks([128.5, 128.7, 128.9]); a.set_yticks([36.3, 36.4, 36.5]); a.tick_params(labelsize=T_SMALL - 1, length=2)
a.set_xticklabels(["128.5°E", "128.7°E", "128.9°E"]); a.set_yticklabels(["36.3°N", "36.4°N", "36.5°N"])
bg.text(2, H - 0.8, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(5.5, H - 0.8, "읍면 고령화지수와 산불 피해 화소(검정)", fontsize=T_HEAD, fontweight="bold", va="top")
bg.add_patch(patches.Rectangle((6.5, 3.2), 21, 7.4, fc="white", ec="none", alpha=0.85, zorder=5))
bg.text(17, 9.4, "고령화지수", fontsize=T_SMALL, ha="center", va="center", zorder=6)
ca = sub_axes(fig, H, 8, 6.0, 18, 1.6)
ca.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=ag_cmap); ca.set_yticks([]); ca.set_xticks([0, 255]); ca.set_xticklabels(["300", "2,500"], fontsize=T_SMALL - 1); ca.tick_params(length=0)
b2 = sub_axes(fig, H, 69, 12, 27, H - 22)
vals = [exf["exposed_aged_idx"], exf["ref_aged_idx"]]
b2.bar([0, 1], vals, color=[RED, POINT["grey"]], width=0.55)
for i, v in enumerate(vals):
    b2.text(i, v + 40, f"{v:,.0f}", ha="center", fontsize=T_BODY, fontweight="bold")
b2.set_xticks([0, 1]); b2.set_xticklabels(["피해 면적\n가중", "분석 범위\n인구 가중"], fontsize=T_SMALL); b2.set_yticks([]); b2.set_ylim(0, 2100)
[b2.spines[s].set_visible(False) for s in ("top", "right", "left")]
bg.text(63, H - 0.8, "(b)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(66.5, H - 0.8, "고령화지수 비교", fontsize=T_HEAD, fontweight="bold", va="top")
bg.text(82.5, 5.5, f"피해 산림의 {exf['share_in_high_aging'] * 100:.0f}%가\n고령화 상위 절반 읍면", fontsize=T_SMALL, ha="center", va="center", color=RED, fontweight="bold", linespacing=1.3)
save(fig, bg, "fig_exposure")

# ===================== 7. 부여 침수 =====================
fig = plt.figure(figsize=(W, 3.0)); bg = fig.add_axes([0, 0, 1, 1]); H = 100 * 3.0 / W; bg.set_xlim(0, 100); bg.set_ylim(0, H); bg.axis("off")
fb = flood["overlays"]["bounds"]; fc_ = flood["overlays"]["focus"]
a = sub_axes(fig, H, 2, 2, 50, H - 6)
for f in gjw["features"]:
    for rg in rings(f["geometry"]):
        a.add_patch(patches.Polygon(rg, closed=True, fc="#F4F2EE", ec="#BDBDBD", lw=0.4, zorder=1))
a.imshow(np.asarray(Image.open(RES / "flood-buyeo-drainage/flood_change.png").convert("RGBA")), extent=(fb[0], fb[2], fb[1], fb[3]), zorder=2, interpolation="nearest")
a.set_xlim(fc_[0], fc_[2]); a.set_ylim(fc_[1], fc_[3]); a.set_aspect(1 / np.cos(np.radians(36.35)))
a.set_xticks([]); a.set_yticks([])
for nm, lon, lat in [("부여읍", 126.91, 36.275), ("규암면", 126.875, 36.29)]:
    if fc_[0] < lon < fc_[2] and fc_[1] < lat < fc_[3]:
        a.text(lon, lat, nm, fontsize=T_SMALL, color=INK, zorder=4)
bg.text(2, H - 0.8, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(5.5, H - 0.8, "정비 전후 침수 비교(침수 밀집 구역)", fontsize=T_HEAD, fontweight="bold", va="top")
lg = [("#154ea0", "정비 전에만 침수"), ("#be1828", "정비 후에만 침수"), ("#5a2882", "두 시기 모두"), ("#828282", "상시 수역")]
for i, (c, t) in enumerate(lg):
    bg.add_patch(patches.Rectangle((54, H - 12 - i * 4.2), 2.2, 2.2, fc=c, ec="none")); bg.text(57, H - 10.9 - i * 4.2, t, fontsize=T_SMALL, va="center")
b2 = sub_axes(fig, H, 75, 13, 22, H - 25)
ev = [e for e in flood["events"] if (e.get("stage2") or {}).get("flooded_ha") is not None]
b2.bar([0, 1], [mv(flood, "flooded_ha_per_mm_before"), mv(flood, "flooded_ha_per_mm_after")], color=[POINT["navy"], RED], width=0.55)
for i, v in enumerate([mv(flood, "flooded_ha_per_mm_before"), mv(flood, "flooded_ha_per_mm_after")]):
    b2.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=T_BODY, fontweight="bold")
b2.set_xticks([0, 1]); b2.set_xticklabels(["정비 전\n(2023)", "정비 후\n(2025)"], fontsize=T_SMALL); b2.set_yticks([]); b2.set_ylim(0, 1.75)
[b2.spines[s].set_visible(False) for s in ("top", "right", "left")]
bg.text(72, H - 0.8, "(b)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(75.5, H - 0.8, "비 1 mm당 침수 면적", fontsize=T_HEAD, fontweight="bold", va="top")
bg.text(64, 4.2, f"최대 3시간 강우\n80 mm 대 133 mm", fontsize=T_SMALL, ha="center", va="center", color=GREY_M, linespacing=1.3)
save(fig, bg, "fig_flood")

# ===================== 8. 확장 계획 =====================
fig, bg, H = setup(3.4)
phases = [("1단계  2027", "파일럿, 보고서 부록"), ("2단계  2028", "지자체 구독, 공공기관"), ("3단계  2029 이후", "전국 표준, 기업 공시")]
cw = 26.4
for i, (p, s) in enumerate(phases):
    x = 16 + i * (cw + 1.2)
    bg.add_patch(patches.Polygon([(x, H - 9), (x + cw - 1.5, H - 9), (x + cw + 0.5, H - 5.6), (x + cw - 1.5, H - 2.2), (x, H - 2.2), (x + 2, H - 5.6)], closed=True, fc=["#D9D9D9", "#BFBFBF", NAVY][i], ec="none", zorder=1))
    bg.text(x + cw / 2 + 0.5, H - 4.4, p, fontsize=T_BODY, fontweight="bold", ha="center", va="center", color="white" if i == 2 else INK, zorder=2)
    bg.text(x + cw / 2 + 0.5, H - 7.2, s, fontsize=T_SMALL, ha="center", va="center", color="white" if i == 2 else INK, zorder=2)
rows_r = [("사업 유형", ["산불 복원, 옥상 차열,\n배수 정비 3종", "한파 쉼터, 가뭄,\n수변 복원 추가 6종", "해안 침식, 그늘 시설\n적응 사업 전반"]),
          ("고객", ["기초지자체 1곳 무상\n수립 용역 하도급 5건", "지자체 구독 3~6곳\n공공기관 과업", "디지털서비스 전문계약\n상장사 공시 모듈"]),
          ("자료와 설계", ["공개 위성, 공공 API\n사업 대장 수기 입력", "사업 경계 결합\n사업 효과 검증 전환", "다년 기준선 누적\n검정력 상승"]),
          ("지표", ["검증 사업 수\n보고서 인용 건수", "검정력 충족 비율\n재배분 예산액", "전국 동일 기준\n지자체 비교"])]
for j, (rn, cells) in enumerate(rows_r):
    y = H - 18.5 - j * 9.6
    header(bg, 2, y, 13, 8.4, rn, fs=T_BODY)
    for i, c in enumerate(cells):
        proc(bg, 16 + i * (cw + 1.2), y, cw, 8.4, c, fs=T_SMALL, fc="white" if i < 2 else "#EEF2F8")
save(fig, bg, "fig_roadmap")

# ===================== 9. 효용 흐름 =====================
fig, bg, H = setup(2.6)
bg.add_patch(patches.FancyBboxPatch((2, H / 2 - 9), 19, 18, boxstyle="round,pad=0,rounding_size=0.8", fc="white", ec=INK, lw=1.8, zorder=2))
bg.text(11.5, H / 2 + 4.5, "성과 카드", fontsize=T_HEAD, fontweight="bold", color=RED, ha="center", va="center")
bg.text(11.5, H / 2 - 2.5, "사업 1건당\n매년 1장", fontsize=T_SMALL, ha="center", va="center", color=GREY_M, linespacing=1.3)
ben = [("주민, 취약계층", "예산이 고령, 노후 지역에\n닿았는지 공개 확인", f"의성 피해의 {exf['share_in_high_aging'] * 100:.0f}%가 고령 상위 읍면\n길안, 단촌, 일직면 우선 복구"),
       ("지자체 담당, 예산 부서", "효과 미확인 사업의 재설계\n집행 순위의 공개 규칙", "가양 1순위 809동 240세대\n시공 동은 6, 8순위"),
       ("중앙정부, 의회, 감사", "지자체 간 같은 기준 비교\n집행 증빙에서 효과 증빙으로", "이행점검 243곳, 매년 반복\n출처 배지와 재현 매니페스트"),
       ("현장과 생태계", "회복 지연 사면, 반복 침수\n구역의 조기 식별", f"부여 강우 보정 후 {mv(flood, 'flooded_change_pct_rain_adjusted'):+.0f}%\n현장조사 대상 선정")]
for i, (who, what, ev) in enumerate(ben):
    y = H - 10.0 - i * 8.2
    line(bg, [(21.2, H / 2), (25, H / 2), (25, y + 3.5), (28.5, y + 3.5)])
    proc(bg, 28.5, y, 17, 7.0, who, fs=T_SMALL, weight="bold", fc=GREY_F)
    proc(bg, 46.5, y, 25, 7.0, what, fs=T_SMALL)
    proc(bg, 72.5, y, 25.5, 7.0, ev, fs=T_SMALL, fc="#FBF7EE", ec="#BFBFBF")
bg.text(59, H - 1.0, "달라지는 점", fontsize=T_SMALL, ha="center", va="top", color=GREY_M)
bg.text(85, H - 1.0, "시제품 실측 근거", fontsize=T_SMALL, ha="center", va="top", color=GREY_M)
save(fig, bg, "fig_benefit")

# ===================== 10. 산불 회복(시제품 결과 파일 기준) =====================
fig, bg, H = setup(4.05)
fbx = fire["overlays"]["bounds"]
pan = [("(a)", "산불 전 진색 " + fire["scenes"][0]["date"], np.asarray(Image.open(RES / "fire-uiseong-2025/pre.png").convert("RGB"))),
       ("(b)", "진화 직후 진색 " + fire["scenes"][1]["date"], np.asarray(Image.open(RES / "fire-uiseong-2025/post.png").convert("RGB"))),
       ("(c)", "dNBR 피해 정도", over(RES / "fire-uiseong-2025/post.png", RES / "fire-uiseong-2025/dnbr.png", 0.9))]
pw = 31.5; ph = pw * (fbx[3] - fbx[1]) / ((fbx[2] - fbx[0]) * np.cos(np.radians(36.4)))
for i, (lab, tt, arr) in enumerate(pan):
    x = 1.5 + i * (pw + 1.2)
    img_ax(fig, H, x, H - 3.2 - ph, pw, ph, arr)
    bg.text(x, H - 0.6, lab, fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(x + 3.6, H - 0.6, tt, fontsize=T_SMALL, va="top")
sv = fire["severity"]; sx0 = 1.5 + 2 * (pw + 1.2)
for i, (s_, c) in enumerate(zip(sv, ["#f7e26b", "#f29e2e", "#d7301f", "#7a0177"])):
    xx = sx0 + (i % 2) * 15.5; yy = H - 4.6 - ph - (i // 2) * 2.6
    bg.add_patch(patches.Rectangle((xx, yy - 0.9), 1.8, 1.8, fc=c, ec="none"))
    bg.text(xx + 2.3, yy, f"{s_['label'].split('(')[0]} {s_['ha']:,} ha", fontsize=T_SMALL - 0.8, va="center")
ax = sub_axes(fig, H, 8, 3.5, 60, H - 15.0 - ph)
ser = fire["series"]; xs_ = np.arange(len(ser))
ax.fill_between(xs_, [s["burned"]["q25"] for s in ser], [s["burned"]["q75"] for s in ser], color="#8a5a1e", alpha=0.16, lw=0, label="피해지 사분위 범위")
ax.plot(xs_, [s["burned"]["median"] for s in ser], "-o", color="#8a5a1e", lw=1.8, ms=4, label="피해지 중앙값")
ax.plot(xs_, [s["control"]["median"] for s in ser], "--s", color="#2f7d4f", lw=1.4, ms=3.5, label="주변 숲 중앙값")
ax.set_xticks(xs_); ax.set_xticklabels([s["date"] for s in ser], fontsize=T_SMALL - 0.6); ax.set_ylim(0, 1); ax.set_ylabel("NDVI", fontsize=T_SMALL)
ax.tick_params(labelsize=T_SMALL - 0.6); [ax.spines[k].set_visible(False) for k in ("top", "right")]; ax.grid(axis="y", alpha=0.25, lw=0.5)
ax.legend(fontsize=T_SMALL - 0.6, frameon=False, loc="lower right", ncol=3)
bg.text(1.5, H - 9.0 - ph, "(d)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(5.1, H - 9.0 - ph, "피해지와 주변 숲의 식생지수", fontsize=T_SMALL, va="top")
rx = 72
bg.text(rx, H - 9.0 - ph, "(e)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(rx + 3.6, H - 9.0 - ph, "회복률(피해지 ÷ 주변 숲)", fontsize=T_SMALL, va="top")
for i, s in enumerate(ser):
    yy = H - 14.0 - ph - i * 4.4
    lab = {"pre": "산불 전", "post": "진화 직후"}.get(s["label"], s["label"])
    bg.text(rx + 1, yy, lab, fontsize=T_SMALL, va="center")
    bg.add_patch(patches.Rectangle((rx + 13, yy - 1.2), 12 * s["recovery_ratio"], 2.4, fc=RED if i == len(ser) - 1 else POINT["grey"], ec="none"))
    bg.text(rx + 13 + 12 * s["recovery_ratio"] + 0.8, yy, f"{s['recovery_ratio']:.2f}", fontsize=T_SMALL, va="center", fontweight="bold" if i == len(ser) - 1 else "normal")
save(fig, bg, "fig_fire")

# ===================== 11. 화면 합성 =====================
crop = lambda p, box: np.asarray(Image.open(p).convert("RGB").crop(box))
fig, bg, H = setup(5.15)
shots = [("(a)", "산불 피해지, 성과 카드", crop(SHOT / "ui_fire.png", (0, 0, 1500, 900))), ("(b)", "옥상 차열, 3D 건물과 지표면온도", crop(SHOT / "ui_heat.png", (0, 0, 1500, 900))),
         ("(c)", "배수 정비, 정비 전후 침수 비교", crop(SHOT / "ui_flood.png", (0, 0, 1500, 900))), ("(d)", "읍면 고령화와 취약 지역 노출", crop(SHOT / "ui_aging.png", (0, 0, 1500, 900)))]
sw_ = 48.4; sh_ = sw_ * 900 / 1500
for i, (lab, tt, arr) in enumerate(shots):
    r_, c_ = divmod(i, 2); x = 1.0 + c_ * (sw_ + 1.6); y = H - 3.2 - sh_ - r_ * (sh_ + 4.2)
    img_ax(fig, H, x, y, sw_, sh_, arr, border="#7F7F7F")
    bg.text(x, y + sh_ + 2.6, lab, fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(x + 3.6, y + sh_ + 2.6, tt, fontsize=T_SMALL, va="top")
save(fig, bg, "fig_ui")
fig, bg, H = setup(3.75)
sm = crop(SHOT / "ui_summary.png", (0, 0, 1500, 900)); cd = crop(SHOT / "card_fire.png", (40, 20, 880, 1400))
hw = 62; hh = hw * sm.shape[0] / sm.shape[1]
img_ax(fig, H, 1, H - 3.2 - hh, hw, hh, sm, border="#7F7F7F")
bg.text(1, H - 0.6, "(a)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(4.6, H - 0.6, "관할 요약(과장, 의회)", fontsize=T_SMALL, va="top")
cw2 = 36; ch2 = cw2 * cd.shape[0] / cd.shape[1]
if ch2 > H - 4:
    ch2 = H - 4; cw2 = ch2 * cd.shape[1] / cd.shape[0]
img_ax(fig, H, 99 - cw2, H - 3.2 - ch2, cw2, ch2, cd, border="#7F7F7F")
bg.text(99 - cw2, H - 0.6, "(b)", fontsize=T_HEAD, fontweight="bold", va="top"); bg.text(99 - cw2 + 3.6, H - 0.6, "보고서 부록(인쇄 카드)", fontsize=T_SMALL, va="top")
save(fig, bg, "fig_ui_outputs")

for r in report:
    print(r)
