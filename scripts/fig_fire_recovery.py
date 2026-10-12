# -*- coding: utf-8 -*-
"""그림: 2025년 3월 영남(의성) 산불 피해지의 위성 기반 사후검증 예시.
Sentinel-2 L2A (Planetary Computer, 동일 상대궤도 R103, 타일 T52SDF·T52SEF 모자이크)
- 전/후 진색 합성, dNBR 피해등급, 피해지 vs 대조지 NDVI 회복 곡선
처리 기준: Processing Baseline ≥ 04.00 → reflectance = (DN - 1000)/10000, SCL 3·8·9·10·11 마스킹
"""
import json, os, requests, numpy as np, rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from pyproj import Transformer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

OUT = r"C:\for_huss\figures"
os.makedirs(OUT, exist_ok=True)
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
import time
tok = None
for _try in range(6):
    try:
        _r = requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a", timeout=60, headers={"User-Agent": "for_huss-proposal/1.0"})
        if _r.status_code == 200 and _r.text.strip().startswith("{"):
            tok = _r.json()["token"]; break
        print("token retry", _try, _r.status_code, _r.text[:80])
    except Exception as _e:
        print("token retry", _try, type(_e).__name__)
    time.sleep(5 + 5 * _try)
if tok is None:
    raise SystemExit("SAS token unavailable")

# 동일 상대궤도(R003) 장면만 사용 — 조도·기하 조건 통일
scenes = [
    ("2025-03-14", "S2B_MSIL2A_20250314T020659_R103_T52SDF"),   # 산불 전 (발화 03-22)
    ("2025-04-08", "S2C_MSIL2A_20250408T020711_R103_T52SDF"),   # 진화 직후
    ("2025-07-09", "S2A_MSIL2A_20250709T021131_R103_T52SDF"),   # 첫 생장기
    ("2026-06-12", "S2C_MSIL2A_20260612T020651_R103_T52SDF"),   # 2년차 생장기
    ("2026-10-02", "S2A_MSIL2A_20261002T021121_R103_T52SDF"),   # 2년차 말
]
# AOI: 의성군 안평·점곡·옥산면 ~ 안동 길안면 (피해 핵심부), EPSG:4326
bbox = [128.45, 36.26, 128.95, 36.55]
tr = Transformer.from_crs("EPSG:4326", "EPSG:32652", always_xy=True)
x0, y0 = tr.transform(bbox[0], bbox[1]); x1, y1 = tr.transform(bbox[2], bbox[3])
RES = 40.0
W = int((x1 - x0) / RES); H = int((y1 - y0) / RES)
print("AOI px", W, H)

env = rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")
stack = {}
manifest = []
for date, sid in scenes:
    srch = requests.post(f"{STAC}/search", json={"collections": ["sentinel-2-l2a"], "bbox": bbox, "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z", "limit": 20}, timeout=60).json()
    cands = [f for f in srch.get("features", []) if f["id"].startswith(sid)]
    if not cands:
        raise SystemExit(f"scene not found for {sid}: {[f['id'] for f in srch.get('features', [])]}")
    item = cands[0]
    orbit = sid.split("_")[3]
    items = [f for f in srch.get("features", []) if f["id"].split("_")[3] == orbit]   # same pass, neighbouring tiles -> mosaic
    print("tiles", [f["properties"].get("s2:mgrs_tile") for f in items])
    pb = item["properties"].get("s2:processing_baseline")
    cc = item["properties"].get("eo:cloud_cover")
    bands = {}
    with env:
        for b in ["B02", "B03", "B04", "B08", "B12", "SCL"]:
            merged = None
            for it in items:
                href = it["assets"][b]["href"] + "?" + tok
                with rasterio.open(href) as ds:
                    if ds.crs.to_epsg() != 32652:
                        continue
                    win = from_bounds(x0, y0, x1, y1, ds.transform)
                    rs = Resampling.nearest if b == "SCL" else Resampling.average
                    arr = ds.read(1, window=win, out_shape=(H, W), resampling=rs, boundless=True, fill_value=0).astype("float32")
                merged = arr if merged is None else np.where(merged == 0, arr, merged)
            bands[b] = merged
    scl = bands["SCL"]
    bad = np.isin(scl, [0, 1, 3, 8, 9, 10, 11])
    refl = {b: np.where(bad, np.nan, (bands[b] - 1000.0) / 10000.0) for b in ["B02", "B03", "B04", "B08", "B12"]}
    valid = 100 * (1 - bad.mean())
    stack[date] = refl
    manifest.append({"date": date, "id": sid, "processing_baseline": pb, "cloud_cover": cc, "valid_pct_in_aoi": round(float(valid), 1)})
    print(date, sid, "PB", pb, "cc", cc, "valid%", round(valid, 1))

ndvi = {d: (r["B08"] - r["B04"]) / (r["B08"] + r["B04"]) for d, r in stack.items()}
nbr = {d: (r["B08"] - r["B12"]) / (r["B08"] + r["B12"]) for d, r in stack.items()}
pre, post = "2025-03-14", "2025-04-08"
dnbr = nbr[pre] - nbr[post]
forest_pre = ndvi[pre] > 0.30          # 3월 상록·혼효림 기준(낙엽 전 겨울이라 임계 완화)
burn = (dnbr > 0.27) & forest_pre       # Key & Benson(2006) 중등도 이상 → 문화재청 과제와 동일 임계
ctrl = (np.abs(dnbr) < 0.05) & (ndvi[pre] > 0.30) & ~np.isnan(dnbr)
burn_ha = int(round(float(np.nansum(burn)) * RES * RES / 1e4))
print("burn px", int(np.nansum(burn)), "area_ha", burn_ha, "ctrl px", int(np.nansum(ctrl)))

dates = [d for d, _ in scenes]
b_med = [float(np.nanmedian(ndvi[d][burn])) for d in dates]
c_med = [float(np.nanmedian(ndvi[d][ctrl])) for d in dates]
b_q1 = [float(np.nanpercentile(ndvi[d][burn], 25)) for d in dates]
b_q3 = [float(np.nanpercentile(ndvi[d][burn], 75)) for d in dates]
ratio = [b / c for b, c in zip(b_med, c_med)]
print("burned NDVI median", [round(v, 3) for v in b_med]); print("control", [round(v, 3) for v in c_med]); print("ratio", [round(v, 3) for v in ratio])

# 피해등급 (Key & Benson 2006, USGS 기준)
cls = np.full(dnbr.shape, np.nan)
cls[(dnbr >= 0.10) & (dnbr < 0.27)] = 1
cls[(dnbr >= 0.27) & (dnbr < 0.44)] = 2
cls[(dnbr >= 0.44) & (dnbr < 0.66)] = 3
cls[dnbr >= 0.66] = 4
area = {k: round(float(np.nansum(cls == k)) * RES * RES / 1e4) for k in [1, 2, 3, 4]}
print("severity area ha", area)

rgb = lambda r: np.clip(np.dstack([r["B04"], r["B03"], r["B02"]]) / 0.30, 0, 1)
ext = [bbox[0], bbox[2], bbox[1], bbox[3]]

fig = plt.figure(figsize=(7.2, 5.3), dpi=200)
gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.15], hspace=0.05, wspace=0.12)
ax1 = fig.add_subplot(gs[0, 0]); ax1.imshow(np.nan_to_num(rgb(stack[pre]), nan=1.0), extent=ext); ax1.set_title("(a) 산불 전 2025-03-14", fontsize=9)
ax2 = fig.add_subplot(gs[0, 1]); ax2.imshow(np.nan_to_num(rgb(stack[post]), nan=1.0), extent=ext); ax2.set_title("(b) 진화 직후 2025-04-08", fontsize=9)
ax3 = fig.add_subplot(gs[0, 2])
cmap = colors.ListedColormap(["#fde68a", "#fb923c", "#dc2626", "#581c87"])
ax3.imshow(np.nan_to_num(rgb(stack[post]), nan=1.0), extent=ext, alpha=0.35)
im = ax3.imshow(np.ma.masked_invalid(cls), extent=ext, cmap=cmap, vmin=0.5, vmax=4.5, interpolation="nearest")
ax3.set_title("(c) dNBR 피해등급", fontsize=9)
for a in (ax1, ax2, ax3):
    a.set_xticks([]); a.set_yticks([])
cb = fig.colorbar(im, ax=ax3, fraction=0.046, pad=0.02, ticks=[1, 2, 3, 4]); cb.ax.set_yticklabels(["경", "중", "중강", "강"], fontsize=7)

ax4 = fig.add_subplot(gs[1, :])
xs = np.arange(len(dates))
ax4.fill_between(xs, b_q1, b_q3, color="#dc2626", alpha=0.15, label="피해지 사분위 범위")
ax4.plot(xs, b_med, "o-", color="#dc2626", lw=1.8, label=f"피해지 중앙값 (dNBR>0.27, {burn_ha:,} ha)")
ax4.plot(xs, c_med, "s--", color="#166534", lw=1.6, label="대조지 중앙값 (|dNBR|<0.05, 미피해 산림)")
for i, r in enumerate(ratio):
    ax4.annotate(f"{r:.2f}", (xs[i], b_med[i]), textcoords="offset points", xytext=(0, 9 if i == 0 else -14), ha="center", fontsize=7.5, color="#7f1d1d")
ax4.axvline(0.5, color="k", lw=0.8, ls=":"); ax4.text(0.52, ax4.get_ylim()[1] * 0.98 if False else 0.86, "발화 2025-03-22", fontsize=7.5, va="top")
ax4.set_xticks(xs); ax4.set_xticklabels(dates, fontsize=8); ax4.set_ylabel("NDVI (중앙값)", fontsize=9)
ax4.set_ylim(0, 0.9); ax4.grid(alpha=0.25)
ax4.set_title("(d) 피해지 식생 회복 추적 — 숫자는 피해지/대조지 NDVI 비(=회복률)", fontsize=9)
ax4.legend(fontsize=7.5, loc="lower right", frameon=False)
fig.text(0.01, 0.005, "자료: Copernicus Sentinel-2 L2A (Microsoft Planetary Computer), 상대궤도 R103 동일 조건, 40 m 재표집, SCL 구름·그림자 마스킹. 피해등급 임계는 Key & Benson(2006).", fontsize=6.5, color="#444")
fig.savefig(os.path.join(OUT, "fig_fire_recovery.png"), bbox_inches="tight")
fig.savefig(os.path.join(OUT, "fig_fire_recovery.svg"), bbox_inches="tight")

json.dump({"aoi_bbox_4326": bbox, "resolution_m": RES, "scenes": manifest, "burned_forest_ha_dnbr_gt_0_27": burn_ha, "severity_area_ha": area,
           "ndvi_burned_median": b_med, "ndvi_control_median": c_med, "recovery_ratio": ratio, "dates": dates},
          open(os.path.join(OUT, "fig_fire_recovery.manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("saved")
