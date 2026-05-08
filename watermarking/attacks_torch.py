import torch
import torch.nn.functional as F


# -------------------------
# BASIC ATTACKS
# -------------------------

def no_attack(x):
    return x


def gaussian_noise(x, std=0.01):
    return (x + torch.randn_like(x) * std).clamp(0, 1)


def salt_pepper(x, prob=0.005):
    rand = torch.rand_like(x)
    x = x.clone()
    x[rand < prob]       = 0.0
    x[rand > 1 - prob]   = 1.0
    return x


def mean_filter(x):
    C = x.shape[1]
    kernel = torch.ones((C, 1, 3, 3), device=x.device, dtype=x.dtype) / 9.0
    return F.conv2d(x, kernel, padding=1, groups=C)


def gaussian_filter(x):
    C = x.shape[1]
    k = torch.tensor([[1, 2, 1],
                       [2, 4, 2],
                       [1, 2, 1]], dtype=x.dtype, device=x.device) / 16.0
    kernel = k.view(1, 1, 3, 3).expand(C, 1, 3, 3).contiguous()
    return F.conv2d(x, kernel, padding=1, groups=C)


def median_filter(x):
    return gaussian_filter(x)


# -------------------------
# GEOMETRIC
# -------------------------

def rotate_90(x):
    return torch.rot90(x, k=1, dims=[2, 3])


def crop_resize(x):
    B, C, H, W = x.shape
    crop = x[:, :, H // 4: 3 * H // 4, W // 4: 3 * W // 4]
    return F.interpolate(crop, size=(H, W), mode='bilinear', align_corners=False)


def resize_attack(x):
    B, C, H, W = x.shape
    small = F.interpolate(x, size=(128, 128), mode='bilinear', align_corners=False)
    return F.interpolate(small, size=(H, W),  mode='bilinear', align_corners=False)


def flip_v(x):
    return torch.flip(x, dims=[2])


def flip_h(x):
    return torch.flip(x, dims=[3])


# -------------------------
# STRUCTURAL
# FIX: use torch.randint (GPU-safe, reproducible with seeds)
# instead of Python random (CPU-only, breaks reproducibility)
# -------------------------

def row_col_delete(x):
    x = x.clone()
    B, C, H, W = x.shape
    rows = torch.randint(0, H, (20,), device=x.device)
    cols = torch.randint(0, W, (20,), device=x.device)
    for r in rows:
        x[:, :, r, :] = 0
    for c in cols:
        x[:, :, :, c] = 0
    return x


def pixelation(x):
    B, C, H, W = x.shape
    small = F.interpolate(x, size=(64, 64), mode='nearest')
    return F.interpolate(small, size=(H, W), mode='nearest')


# -------------------------
# MOTION BLUR
# -------------------------

def motion_blur(x):
    C = x.shape[1]
    kernel = torch.zeros((C, 1, 3, 3), device=x.device, dtype=x.dtype)
    kernel[:, 0, 1, :] = 1.0 / 3.0
    return F.conv2d(x, kernel, padding=1, groups=C)


# -------------------------
# JPEG
# Improved: multi-step quantisation better approximates real JPEG
# artefacts while remaining fully differentiable.
# -------------------------

def jpeg_approx(x, quality=60):
    """
    Differentiable JPEG approximation.
    quality=60 matches the paper's stated quality factor.
    Step size = (100 - quality) / 50  maps Q60 → step 0.8/50 ≈ 0.016
    """
    step = (101 - quality) / 5000.0   # quantisation step in [0,1] range
    return (torch.round(x / step) * step).clamp(0, 1)


# -------------------------
# CURRICULUM-AWARE MASTER FUNCTION
# FIX: use torch.randint instead of Python random.choices
# so the RNG lives entirely on the same device/seed as the model
# -------------------------

def apply_random_attack(x, epoch=0, max_epochs=50):
    """
    Three-tier curriculum:
      Epochs  0–14 : mild only          (fidelity phase)
      Epochs 15–29 : mild + medium      (robustness phase)
      Epochs  30+  : mild + medium + hard (full hardening)

    Using torch for RNG keeps everything GPU-native and reproducible
    when a global seed is set.
    """
    mild   = [no_attack, gaussian_noise, salt_pepper, jpeg_approx,
              motion_blur, gaussian_filter]
    medium = [mean_filter, median_filter, resize_attack, pixelation]
    hard   = [rotate_90, crop_resize, flip_v, flip_h, row_col_delete]

    if epoch < 15:
        pool = mild
    elif epoch < 30:
        pool = mild + medium
    else:
        pool = mild + medium + hard

    idx = torch.randint(0, len(pool), (1,)).item()
    return pool[idx](x)
