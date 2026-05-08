"""
Run on the cluster BEFORE training to verify all transforms are lossless.
Usage: python verify_pipeline.py
Expected: all three lines show PSNR > 100 dB
"""
import torch, sys
from transforms.dwt_torch import dwt2, idwt2
from transforms.dct_torch import dct2, idct2

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}\n")

ok = True
with torch.no_grad():
    x = torch.rand(4, 1, 128, 128, device=device)

    # DWT round-trip
    xr = idwt2(*dwt2(x))
    mse = torch.mean((x - xr)**2).item()
    p = 20*torch.log10(torch.tensor(1/(mse**0.5+1e-15))).item()
    status = "✓ OK" if p > 100 else "✗ BROKEN"
    print(f"DWT  round-trip PSNR: {p:7.1f} dB  {status}")
    if p <= 100: ok = False

    # DCT round-trip
    yr = idct2(dct2(x))
    mse2 = torch.mean((x - yr)**2).item()
    p2 = 20*torch.log10(torch.tensor(1/(mse2**0.5+1e-15))).item()
    status2 = "✓ OK" if p2 > 100 else "✗ BROKEN"
    print(f"DCT  round-trip PSNR: {p2:7.1f} dB  {status2}")
    if p2 <= 100: ok = False

    # Full pipeline with zero embedding
    LL, LH, HL, HH = dwt2(x)
    xr2 = idwt2(LL, idct2(dct2(LH)), idct2(dct2(HL)), HH)
    mse3 = torch.mean((x - xr2)**2).item()
    p3 = 20*torch.log10(torch.tensor(1/(mse3**0.5+1e-15))).item()
    status3 = "✓ OK" if p3 > 100 else "✗ BROKEN"
    print(f"Full pipeline  PSNR: {p3:7.1f} dB  {status3}")
    if p3 <= 100: ok = False

print()
if ok:
    print("All transforms lossless. PSNR limited only by embedding strength.")
    print("With embedder.max_delta=0.01, expect training PSNR > 55 dB.")
else:
    print("FATAL: broken transform detected. Fix before training.")
    sys.exit(1)
