import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

os.makedirs("results", exist_ok=True)

# Load per-attack results
rows = list(csv.DictReader(open("results/per_attack_metrics.csv")))
attacks = [r["Attack"] for r in rows]
psnr    = [float(r["PSNR"]) for r in rows]
ber     = [float(r["BER"])  for r in rows]
ssim    = [float(r["SSIM"]) for r in rows]
nc      = [float(r["NC"])   for r in rows]

x = np.arange(len(attacks))
bar_color   = '#2E86C1'
edge_color  = '#1A5276'

def style_ax(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, axis='y', linestyle='--', alpha=0.4, color='#CCCCCC')
    ax.tick_params(labelsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(attacks, fontsize=9)

# ── Figure 1: BER + NC per attack ────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
fig.patch.set_facecolor('white')

ax = axes[0]
bars = ax.bar(x, ber, color=bar_color, edgecolor=edge_color, linewidth=0.6, width=0.6)
ax.set_ylabel("BER", fontsize=11)
ax.set_title("Bit Error Rate (BER) per Attack", fontsize=12, fontweight='bold')
ax.set_xlabel("Attack Type", fontsize=10)
style_ax(ax)
# Value labels on bars
for bar, v in zip(bars, ber):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.0005,
            f'{v:.3f}', ha='center', va='bottom', fontsize=7.5)

ax = axes[1]
bars = ax.bar(x, nc, color='#1E8449', edgecolor='#145A32', linewidth=0.6, width=0.6)
ax.set_ylabel("NC Score", fontsize=11)
ax.set_title("Normalized Correlation (NC) per Attack", fontsize=12, fontweight='bold')
ax.set_xlabel("Attack Type", fontsize=10)
ax.set_ylim(0.98, 1.002)
style_ax(ax)
for bar, v in zip(bars, nc):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.0001,
            f'{v:.4f}', ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig("results/test_ber_nc.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print("Saved test_ber_nc.png")

# ── Figure 2: PSNR + SSIM per attack ─────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
fig.patch.set_facecolor('white')

ax = axes[0]
bars = ax.bar(x, psnr, color=bar_color, edgecolor=edge_color, linewidth=0.6, width=0.6)
ax.set_ylabel("PSNR (dB)", fontsize=11)
ax.set_title("PSNR per Attack", fontsize=12, fontweight='bold')
ax.set_xlabel("Attack Type", fontsize=10)
psnr_min = min(psnr)
ax.set_ylim(psnr_min - 0.5, max(psnr) + 0.5)
style_ax(ax)
for bar, v in zip(bars, psnr):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.02,
            f'{v:.1f}', ha='center', va='bottom', fontsize=7.5)

ax = axes[1]
bars = ax.bar(x, ssim, color='#1E8449', edgecolor='#145A32', linewidth=0.6, width=0.6)
ax.set_ylabel("SSIM", fontsize=11)
ax.set_title("SSIM per Attack", fontsize=12, fontweight='bold')
ax.set_xlabel("Attack Type", fontsize=10)
ssim_min = min(ssim)
ax.set_ylim(ssim_min - 0.0002, max(ssim) + 0.0002)
style_ax(ax)
for bar, v in zip(bars, ssim):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.00002,
            f'{v:.4f}', ha='center', va='bottom', fontsize=7.0)

plt.tight_layout()
plt.savefig("results/test_psnr_ssim.png", dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print("Saved test_psnr_ssim.png")
