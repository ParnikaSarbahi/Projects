import torch
import torch.nn.functional as F
import math


def calculate_psnr(original, watermarked):
    orig = original.detach().float()
    wm   = watermarked.detach().float()
    mse  = torch.mean((orig - wm) ** 2).item()
    if mse < 1e-10:
        return 80.0
    return 20.0 * math.log10(1.0 / math.sqrt(mse))


def calculate_ber(original_wm, recovered_wm):
    original  = (original_wm.detach()  > 0.5).int()
    recovered = (recovered_wm.detach() > 0.5).int()
    errors    = torch.sum(original != recovered)
    return (errors.float() / original.numel()).item()


def calculate_nc(original_wm, recovered_wm):
    w     = original_wm.detach().float().flatten()
    w_hat = recovered_wm.detach().float().flatten()
    num   = torch.sum(w * w_hat)
    denom = torch.sqrt(torch.sum(w ** 2) * torch.sum(w_hat ** 2))
    if denom.item() == 0:
        return 0.0
    return (num / denom).item()


def ssim_torch(x, y):
    C1 = 0.01 ** 2
    C2 = 0.03 ** 2
    mu_x = F.avg_pool2d(x, 3, 1, 1)
    mu_y = F.avg_pool2d(y, 3, 1, 1)
    sigma_x  = F.avg_pool2d(x * x, 3, 1, 1) - mu_x ** 2
    sigma_y  = F.avg_pool2d(y * y, 3, 1, 1) - mu_y ** 2
    sigma_xy = F.avg_pool2d(x * y, 3, 1, 1) - mu_x * mu_y
    ssim_map = ((2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)) /                ((mu_x ** 2 + mu_y ** 2 + C1) * (sigma_x + sigma_y + C2))
    return ssim_map.mean()


def calculate_ssim(x, y):
    with torch.no_grad():
        return ssim_torch(x.float(), y.float()).item()
