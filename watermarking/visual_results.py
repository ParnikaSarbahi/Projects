import torch
import os
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from torch.utils.data import DataLoader, random_split

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
for ckpt_path in ["models/final_model_v2.pth",
                  "models/best_model.pth",
                  "models/final_model_p4.pth"]:
    if os.path.exists(ckpt_path):
        checkpoint = torch.load(ckpt_path, map_location=device)
        print(f"Loaded : {ckpt_path}")
        print(f"Epoch  : {checkpoint.get('epoch','?')}")
        print(f"PSNR   : {checkpoint.get('psnr', 0):.2f} dB")
        print(f"BER    : {checkpoint.get('ber',  1):.4f}")
        print(f"NC     : {checkpoint.get('nc',   0):.4f}")
        break

# ── Models ────────────────────────────────────────────────────────────────────
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
    print("WARNING: legacy single-encoder checkpoint")
else:
    raise KeyError(f"No encoder key found. Keys: {list(checkpoint.keys())}")

transformer.load_state_dict(checkpoint["transformer"])
embedder.load_state_dict(checkpoint["embedder"])
decoder.load_state_dict(checkpoint["decoder"])

enc_embed.eval(); enc_decode.eval()
transformer.eval(); embedder.eval(); decoder.eval()

# ── Pipeline functions ────────────────────────────────────────────────────────
def embed(cover, wm):
    """Full embedding path with new architecture."""
    LL, LH, HL, HH = dwt2(cover)
    LH_dct, HL_dct = dct2(LH), dct2(HL)
    feats, _, _     = enc_embed(torch.cat([LH_dct, HL_dct], dim=1))
    feats           = transformer(feats)
    LH_mod, HL_mod, _, _ = embedder(feats, LH_dct, HL_dct, wm)
    return idwt2(LL, idct2(LH_mod), idct2(HL_mod), HH).clamp(0, 1)


def decode(attacked):
    """Full extraction path with U-Net skip connections."""
    LL2, LH2, HL2, _ = dwt2(attacked)
    feats, skip2, skip1 = enc_decode(torch.cat([dct2(LH2), dct2(HL2)], dim=1))
    feats  = transformer(feats)
    logits = decoder(feats, skip2, skip1)
    return torch.sigmoid(logits)


# ── Data ──────────────────────────────────────────────────────────────────────
covers     = CoverDataset("dataset/cats_dogs")
watermarks = load_logo_watermarks()

# Use test split — same seed as training
train_size  = int(0.8 * len(covers))
test_size   = len(covers) - train_size
generator   = torch.Generator().manual_seed(42)
_, test_set = random_split(covers, [train_size, test_size], generator=generator)

# All 15 attacks as defined in paper Table II
attack_fns = {
    "NO":   no_attack,
    "GN":   gaussian_noise,
    "SP":   salt_pepper,
    "MF":   mean_filter,
    "GF":   gaussian_filter,
    "MD":   median_filter,
    "RO":   rotate_90,
    "CR":   crop_resize,
    "RS":   resize_attack,
    "FR":   flip_v,
    "FC":   flip_h,
    "RCD":  row_col_delete,
    "MB":   motion_blur,
    "PI":   pixelation,
    "JPEG": jpeg_approx,
}

# ── Per-attack evaluation ─────────────────────────────────────────────────────
N_SAMPLES = min(10, len(test_set), len(watermarks))
results   = {}

# Pick diverse test images from test split
test_indices = list(range(0, len(test_set), len(test_set) // N_SAMPLES))[:N_SAMPLES]

with torch.no_grad():
    cover_imgs = [test_set[i].unsqueeze(0).to(device) for i in test_indices]
    wm_indices = list(range(N_SAMPLES))
    wm_imgs = []
    for i in wm_indices:
        wm, _ = watermarks[i % len(watermarks)]
        wm = wm.unsqueeze(0).float().clamp(0, 1).to(device)
        if wm.dim() == 3:    wm = wm.unsqueeze(1)
        if wm.shape[1] != 1: wm = wm.mean(dim=1, keepdim=True)
        wm_imgs.append(wm)

    print(f"\nEvaluating {N_SAMPLES} samples across {len(attack_fns)} attacks...")

    for name, fn in attack_fns.items():
        psnr_acc = ber_acc = ssim_acc = nc_acc = 0.0
        for cover, wm in zip(cover_imgs, wm_imgs):
            wm_exp      = wm.expand(cover.shape[0], -1, -1, -1)
            watermarked = embed(cover, wm_exp)
            attacked    = fn(watermarked)
            recovered   = decode(attacked)
            psnr_acc += calculate_psnr(cover, watermarked)
            ber_acc  += calculate_ber(wm_exp, recovered)
            ssim_acc += calculate_ssim(cover, watermarked)
            nc_acc   += calculate_nc(wm_exp, recovered)

        results[name] = {
            "psnr": psnr_acc / N_SAMPLES,
            "ber":  ber_acc  / N_SAMPLES,
            "ssim": ssim_acc / N_SAMPLES,
            "nc":   nc_acc   / N_SAMPLES,
        }

# ── Print results table ───────────────────────────────────────────────────────
print("\n========== PER-ATTACK RESULTS ==========")
print(f"{'Attack':<8} {'PSNR':>8} {'BER':>8} {'SSIM':>12} {'NC':>8}")
print("-" * 50)
for name, m in results.items():
    flag = " <-- spatial aliasing" if name in ["CR", "RS", "PI"] else ""
    print(f"{name:<8} {m['psnr']:>8.2f} {m['ber']:>8.4f} "
          f"{m['ssim']:>12.6f} {m['nc']:>8.4f}{flag}")

avg_psnr = sum(m['psnr'] for m in results.values()) / len(results)
avg_ber  = sum(m['ber']  for m in results.values()) / len(results)
avg_ssim = sum(m['ssim'] for m in results.values()) / len(results)
avg_nc   = sum(m['nc']   for m in results.values()) / len(results)
print(f"\n{'AVG':<8} {avg_psnr:>8.2f} {avg_ber:>8.4f} {avg_ssim:>12.6f} {avg_nc:>8.4f}")

# Save CSV for plot_attacks.py
with open("results/per_attack_metrics.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Attack", "PSNR", "BER", "SSIM", "NC"])
    for name, m in results.items():
        w.writerow([name, m['psnr'], m['ber'], m['ssim'], m['nc']])
print("\nSaved results/per_attack_metrics.csv")

# ── Figure 2: Paper-style 2x4 visual grid ────────────────────────────────────
# Shows 2 image pairs: cover | watermark | watermarked | recovered
print("\nGenerating Figure 2 (visual comparison grid)...")

with torch.no_grad():
    fig, axes = plt.subplots(2, 4, figsize=(14, 7))
    fig.patch.set_facecolor('white')

    col_titles = ["Cover Image", "Watermark", "Watermarked Image", "Recovered Watermark"]
    for col, title in enumerate(col_titles):
        axes[0, col].set_title(title, fontsize=11, fontweight='bold', pad=10)

    for row in range(2):
        cover = cover_imgs[row]
        wm    = wm_imgs[row].expand(cover.shape[0], -1, -1, -1)
        watermarked = embed(cover, wm)
        recovered   = decode(watermarked)

        psnr_val = calculate_psnr(cover, watermarked)
        ber_val  = calculate_ber(wm, recovered)
        nc_val   = calculate_nc(wm, recovered)

        imgs = [
            cover[0, 0].cpu().numpy(),
            wm[0, 0].cpu().numpy(),
            watermarked[0, 0].cpu().numpy(),
            recovered[0, 0].cpu().numpy(),
        ]

        for col, img in enumerate(imgs):
            axes[row, col].imshow(img, cmap='gray', vmin=0, vmax=1)
            axes[row, col].axis('off')

        # Metrics as row label
        axes[row, 0].set_ylabel(
            f"PSNR={psnr_val:.2f} dB\nBER={ber_val:.4f}  NC={nc_val:.4f}",
            fontsize=8.5, labelpad=8, rotation=90, va='center')

    plt.tight_layout(pad=1.5)
    plt.savefig("results/visual_comparison.png", dpi=200,
                bbox_inches='tight', facecolor='white')
    plt.close()
    print("Saved results/visual_comparison.png")

print("\nAll done.")