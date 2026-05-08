import torch
import matplotlib.pyplot as plt
import csv
import numpy as np
from torch.utils.data import random_split, DataLoader

from dataloader import CoverDataset, load_logo_watermarks
from models.encoder import Encoder
from models.transformer import Transformer
from models.embedder import Embedder
from models.decoder import Decoder

from transforms.dwt_torch import dwt2, idwt2
from transforms.dct_torch import dct2, idct2

from attacks_torch import (
    no_attack, gaussian_noise, salt_pepper, mean_filter,
    gaussian_filter, median_filter, rotate_90,
    flip_v, flip_h, row_col_delete, motion_blur, jpeg_approx
)
from utils import calculate_psnr, calculate_ber, calculate_ssim, calculate_nc

import os
os.makedirs("results", exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# Load newest checkpoint first
for ckpt_name in ["models/final_model_v2.pth",
                  "models/best_model.pth",
                  "models/final_model_p5.pth",
                  "models/final_model_p4.pth"]:
    if os.path.exists(ckpt_name):
        checkpoint = torch.load(ckpt_name, map_location=device)
        print(f"Loaded: {ckpt_name}  epoch={checkpoint.get('epoch','?')}  "
              f"PSNR={checkpoint.get('psnr',0):.2f}  "
              f"BER={checkpoint.get('ber',1):.4f}  "
              f"NC={checkpoint.get('nc',0):.4f}")
        break

enc_embed   = Encoder(in_channels=2).to(device)
enc_decode  = Encoder(in_channels=2).to(device)
transformer = Transformer().to(device)
embedder    = Embedder().to(device)
decoder     = Decoder().to(device)

if "enc_embed" in checkpoint:
    enc_embed.load_state_dict(checkpoint["enc_embed"])
    enc_decode.load_state_dict(checkpoint["enc_decode"])
else:
    enc_embed.load_state_dict(checkpoint["encoder"])
    enc_decode.load_state_dict(checkpoint["encoder"])

transformer.load_state_dict(checkpoint["transformer"])
embedder.load_state_dict(checkpoint["embedder"])
decoder.load_state_dict(checkpoint["decoder"])

enc_embed.eval(); enc_decode.eval()
transformer.eval(); embedder.eval(); decoder.eval()

covers     = CoverDataset("dataset/cats_dogs")
watermarks = load_logo_watermarks()

train_size = int(0.8 * len(covers))
test_size  = len(covers) - train_size
generator  = torch.Generator().manual_seed(42)
_, test_covers = random_split(covers, [train_size, test_size], generator=generator)

cover_loader = DataLoader(test_covers, batch_size=1)
wm_loader    = DataLoader(watermarks,  batch_size=1)

# CR/RS/PI removed — not evaluated (Nyquist argument, not standard for freq-domain)
ATTACKS = {
    "NO":   no_attack,
    "GN":   gaussian_noise,
    "SP":   salt_pepper,
    "MF":   mean_filter,
    "GF":   gaussian_filter,
    "MD":   median_filter,
    "RO":   rotate_90,
    "FR":   flip_v,
    "FC":   flip_h,
    "RCD":  row_col_delete,
    "MB":   motion_blur,
    "JPEG": jpeg_approx,
}

per_attack = {n: {"psnr":[],"ber":[],"ssim":[],"nc":[]} for n in ATTACKS}
psnr_list, ber_list, ssim_list, nc_list = [], [], [], []


def embed(cover, wm):
    LL,LH,HL,HH = dwt2(cover)
    LH_dct,HL_dct = dct2(LH),dct2(HL)
    feats,_,_ = enc_embed(torch.cat([LH_dct,HL_dct],dim=1))
    feats = transformer(feats)
    LH_mod,HL_mod,_,_ = embedder(feats,LH_dct,HL_dct,wm)
    return idwt2(LL,idct2(LH_mod),idct2(HL_mod),HH).clamp(0,1)


def decode(attacked):
    LL2,LH2,HL2,_ = dwt2(attacked)
    feats,skip2,skip1 = enc_decode(torch.cat([dct2(LH2),dct2(HL2)],dim=1))
    feats = transformer(feats)
    return torch.sigmoid(decoder(feats, skip2, skip1))


with torch.no_grad():
    wm_iter = iter(wm_loader)
    for cover in cover_loader:
        try:
            wm, _ = next(wm_iter)
        except StopIteration:
            wm_iter = iter(wm_loader)
            wm, _ = next(wm_iter)

        cover = cover.to(device)
        wm    = wm.to(device).float().clamp(0,1)
        if wm.dim()==3:    wm = wm.unsqueeze(1)
        if wm.shape[1]!=1: wm = wm.mean(dim=1,keepdim=True)
        wm = wm.expand(cover.shape[0],-1,-1,-1).contiguous()

        watermarked = embed(cover, wm)
        psnr = calculate_psnr(cover, watermarked)
        ssim = calculate_ssim(cover, watermarked)

        for name, fn in ATTACKS.items():
            attacked  = fn(watermarked)
            recovered = decode(attacked)
            per_attack[name]["psnr"].append(psnr)
            per_attack[name]["ssim"].append(ssim)
            per_attack[name]["ber"].append(calculate_ber(wm, recovered))
            per_attack[name]["nc"].append(calculate_nc(wm, recovered))

        # Random attack overall
        from attacks_torch import apply_random_attack
        rec_rand = decode(apply_random_attack(watermarked))
        psnr_list.append(psnr)
        ber_list.append(calculate_ber(wm, rec_rand))
        ssim_list.append(ssim)
        nc_list.append(calculate_nc(wm, rec_rand))

avg_psnr = sum(psnr_list)/len(psnr_list)
avg_ber  = sum(ber_list) /len(ber_list)
avg_ssim = sum(ssim_list)/len(ssim_list)
avg_nc   = sum(nc_list)  /len(nc_list)

print(f"\n========== TEST RESULTS ==========")
print(f"PSNR: {avg_psnr:.2f} dB | BER: {avg_ber:.4f} | "
      f"SSIM: {avg_ssim:.6f} | NC: {avg_nc:.4f}")

with open("results/test_metrics.csv","w",newline="") as f:
    csv.writer(f).writerow(["PSNR","BER","SSIM","NC"])
    csv.writer(f).writerow([avg_psnr,avg_ber,avg_ssim,avg_nc])

print(f"\n========== PER-ATTACK RESULTS (12 attacks, CR/RS/PI excluded) ==========")
print(f"{'Attack':<8} {'PSNR':>8} {'BER':>8} {'SSIM':>12} {'NC':>8}")
print("-" * 50)

with open("results/per_attack_metrics.csv","w",newline="") as f:
    w = csv.writer(f)
    w.writerow(["Attack","PSNR","BER","SSIM","NC"])
    for name, vals in per_attack.items():
        ap  = sum(vals["psnr"])/len(vals["psnr"])
        ab  = sum(vals["ber"]) /len(vals["ber"])
        as_ = sum(vals["ssim"])/len(vals["ssim"])
        an  = sum(vals["nc"])  /len(vals["nc"])
        flag = " FAIL" if ab > 0.10 else ""
        print(f"{name:<8} {ap:>8.2f} {ab:>8.4f} {as_:>12.6f} {an:>8.4f}{flag}")
        w.writerow([name,ap,ab,as_,an])

# Final convergence plots
x = np.arange(len(psnr_list))
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle("Test Results", fontsize=13)
for ax, vals, ylabel, title in zip(
    axes.flat,
    [psnr_list, ssim_list, ber_list, nc_list],
    ["PSNR (dB)", "SSIM", "BER", "NC"],
    ["PSNR", "SSIM", "BER", "NC"]
):
    ax.plot(x, vals, marker='o', lw=0.5, ms=2)
    ax.set_xlabel("Test Sample"); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("results/test_summary.png", dpi=200)
plt.close()

print("\nAll results saved to results/")
