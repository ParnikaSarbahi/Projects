import torch
import os
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from torch.utils.data import random_split

from models.encoder import Encoder
from models.transformer import Transformer
from models.embedder import Embedder
from models.decoder import Decoder
from dataloader import CoverDataset, load_logo_watermarks
from transforms.dwt_torch import dwt2, idwt2
from transforms.dct_torch import dct2, idct2
from utils import calculate_psnr, calculate_ber, calculate_ssim, calculate_nc
from attacks_torch import (no_attack, gaussian_noise, salt_pepper, mean_filter,
                            gaussian_filter, median_filter, rotate_90, crop_resize,
                            resize_attack, flip_v, flip_h, row_col_delete,
                            pixelation, motion_blur, jpeg_approx)

os.makedirs("results", exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# ── Load checkpoint ───────────────────────────────────────────────────────────
for ckpt_path in ["models/final_model_v2.pth", "models/best_model.pth"]:
    if os.path.exists(ckpt_path):
        checkpoint = torch.load(ckpt_path, map_location=device)
        print(f"Loaded : {ckpt_path}  "
              f"epoch={checkpoint.get('epoch','?')}  "
              f"PSNR={checkpoint.get('psnr',0):.2f}  "
              f"BER={checkpoint.get('ber',1):.4f}")
        break

enc_embed   = Encoder(in_channels=2).to(device)
enc_decode  = Encoder(in_channels=2).to(device)
transformer = Transformer().to(device)
embedder    = Embedder().to(device)
decoder     = Decoder().to(device)

if "enc_embed" in checkpoint:
    enc_embed.load_state_dict(checkpoint["enc_embed"])
    enc_decode.load_state_dict(checkpoint["enc_decode"])
elif "encoder" in checkpoint:
    enc_embed.load_state_dict(checkpoint["encoder"])
    enc_decode.load_state_dict(checkpoint["encoder"])

transformer.load_state_dict(checkpoint["transformer"])
embedder.load_state_dict(checkpoint["embedder"])
decoder.load_state_dict(checkpoint["decoder"])

enc_embed.eval(); enc_decode.eval()
transformer.eval(); embedder.eval(); decoder.eval()


def embed(cover, wm):
    LL, LH, HL, HH = dwt2(cover)
    LH_dct, HL_dct = dct2(LH), dct2(HL)
    feats, _, _     = enc_embed(torch.cat([LH_dct, HL_dct], dim=1))
    feats           = transformer(feats)
    LH_mod, HL_mod, _, _ = embedder(feats, LH_dct, HL_dct, wm)
    return idwt2(LL, idct2(LH_mod), idct2(HL_mod), HH).clamp(0, 1)


def decode(attacked):
    LL2, LH2, HL2, _ = dwt2(attacked)
    feats, skip2, skip1 = enc_decode(torch.cat([dct2(LH2), dct2(HL2)], dim=1))
    feats  = transformer(feats)
    return torch.sigmoid(decoder(feats, skip2, skip1))


# ── Data ──────────────────────────────────────────────────────────────────────
covers     = CoverDataset("dataset/cats_dogs")
watermarks = load_logo_watermarks()
train_size  = int(0.8 * len(covers))
generator   = torch.Generator().manual_seed(42)
_, test_set = random_split(covers, [train_size, len(covers)-train_size],
                            generator=generator)

with torch.no_grad():
    cover = test_set[0].unsqueeze(0).to(device)
    wm, _ = watermarks[0]
    wm = wm.unsqueeze(0).float().clamp(0, 1).to(device)
    if wm.dim() == 3:    wm = wm.unsqueeze(1)
    if wm.shape[1] != 1: wm = wm.mean(dim=1, keepdim=True)
    wm = wm.expand(cover.shape[0], -1, -1, -1).contiguous()
    watermarked = embed(cover, wm)

# All 15 attacks split into 3 groups of 5
attack_groups = [
    [("NO",   no_attack),
     ("GN",   gaussian_noise),
     ("SP",   salt_pepper),
     ("MF",   mean_filter),
     ("GF",   gaussian_filter)],

    [("MD",   median_filter),
     ("RO",   rotate_90),
     ("FR",   flip_v),
     ("FC",   flip_h),
     ("MB",   motion_blur)],

    [("RCD",  row_col_delete),
     ("JPEG", jpeg_approx),
     ("CR",   crop_resize),
     ("RS",   resize_attack),
     ("PI",   pixelation)],
]

col_headers = ["Attack", "Cover Image", "Watermark",
               "Watermarked Image", "Attacked Image", "Recovered Watermark"]
col_widths  = [0.55, 1, 1, 1, 1, 1]
row_bg      = ['#F4F6F7', '#FFFFFF']
header_bg   = '#1C2833'

cover_np = cover[0, 0].cpu().numpy()
wm_np    = wm[0, 0].cpu().numpy()
wm_np_display = wm_np  # 128x128

all_results = []

for grp_idx, group in enumerate(attack_groups):
    n_rows = len(group)
    fig_h  = n_rows * 1.6 + 0.7
    fig    = plt.figure(figsize=(15, fig_h))
    fig.patch.set_facecolor('white')

    gs = GridSpec(n_rows + 1, 6,
                  width_ratios=col_widths,
                  height_ratios=[0.45] + [1.0] * n_rows,
                  hspace=0.06, wspace=0.03,
                  left=0.01, right=0.99,
                  top=0.98, bottom=0.01)

    # Header row
    for col, header in enumerate(col_headers):
        ax = fig.add_subplot(gs[0, col])
        ax.set_facecolor(header_bg)
        ax.text(0.5, 0.5, header,
                ha='center', va='center',
                fontsize=9, fontweight='bold',
                color='white', transform=ax.transAxes,
                multialignment='center')
        ax.axis('off')

    # Data rows
    with torch.no_grad():
        for row_idx, (atk_name, atk_fn) in enumerate(group):
            attacked  = atk_fn(watermarked)
            recovered = decode(attacked)

            ber  = calculate_ber(wm, recovered)
            nc   = calculate_nc(wm, recovered)
            psnr = calculate_psnr(cover, watermarked)
            ssim = calculate_ssim(cover, watermarked)

            all_results.append({
                "name": atk_name, "psnr": psnr,
                "ber": ber, "ssim": ssim, "nc": nc
            })

            bg         = row_bg[row_idx % 2]
            ber_color  = '#E74C3C' if ber > 0.10 else '#1E8449'
            gs_row     = row_idx + 1   # +1 for header

            # Col 0: attack label + metrics
            ax0 = fig.add_subplot(gs[gs_row, 0])
            ax0.set_facecolor(bg)
            ax0.text(0.5, 0.62, atk_name,
                     ha='center', va='center',
                     fontsize=11, fontweight='bold',
                     color='#1C2833', transform=ax0.transAxes)
            ax0.text(0.5, 0.32, f"BER={ber:.3f}",
                     ha='center', va='center',
                     fontsize=8, color=ber_color,
                     transform=ax0.transAxes)
            ax0.text(0.5, 0.12, f"NC={nc:.3f}",
                     ha='center', va='center',
                     fontsize=8, color='#2471A3',
                     transform=ax0.transAxes)
            ax0.axis('off')

            # Col 1: cover
            ax1 = fig.add_subplot(gs[gs_row, 1])
            ax1.imshow(cover_np, cmap='gray', vmin=0, vmax=1)
            ax1.axis('off')

            # Col 2: watermark
            ax2 = fig.add_subplot(gs[gs_row, 2])
            ax2.imshow(wm_np_display, cmap='gray', vmin=0, vmax=1)
            ax2.axis('off')

            # Col 3: watermarked
            ax3 = fig.add_subplot(gs[gs_row, 3])
            ax3.imshow(watermarked[0, 0].cpu().numpy(), cmap='gray', vmin=0, vmax=1)
            ax3.text(0.5, -0.04, f"PSNR={psnr:.1f}dB",
                     ha='center', va='top', fontsize=7,
                     color='#555555', transform=ax3.transAxes)
            ax3.axis('off')

            # Col 4: attacked
            ax4 = fig.add_subplot(gs[gs_row, 4])
            ax4.imshow(attacked[0, 0].cpu().numpy(), cmap='gray', vmin=0, vmax=1)
            ax4.axis('off')

            # Col 5: recovered
            ax5 = fig.add_subplot(gs[gs_row, 5])
            ax5.imshow(recovered[0, 0].cpu().numpy(), cmap='gray', vmin=0, vmax=1)
            ax5.axis('off')

    fname = f"results/attack_grid_{grp_idx+1}.png"
    plt.savefig(fname, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved {fname}")

# ── Save CSV ──────────────────────────────────────────────────────────────────
with open("results/per_attack_metrics.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Attack", "PSNR", "BER", "SSIM", "NC"])
    for r in all_results:
        w.writerow([r['name'], r['psnr'], r['ber'], r['ssim'], r['nc']])
print("Saved results/per_attack_metrics.csv")

# Print summary
print("\n========== SUMMARY ==========")
print(f"{'Attack':<8} {'PSNR':>8} {'BER':>8} {'SSIM':>12} {'NC':>8}")
print("-" * 50)
for r in all_results:
    flag = " FAIL" if r['ber'] > 0.10 else ""
    print(f"{r['name']:<8} {r['psnr']:>8.2f} {r['ber']:>8.4f} "
          f"{r['ssim']:>12.6f} {r['nc']:>8.4f}{flag}")