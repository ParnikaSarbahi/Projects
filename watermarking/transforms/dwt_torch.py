import torch


def dwt2(x):
    """
    2D Haar DWT — lifting scheme, exact and invertible.
    x      : (B, 1, H, W)
    returns: LL, LH, HL, HH  each (B, 1, H/2, W/2)
    """
    L = (x[:, :, :, 0::2] + x[:, :, :, 1::2]) * 0.5
    H = (x[:, :, :, 0::2] - x[:, :, :, 1::2]) * 0.5
    LL = (L[:, :, 0::2, :] + L[:, :, 1::2, :]) * 0.5
    LH = (L[:, :, 0::2, :] - L[:, :, 1::2, :]) * 0.5
    HL = (H[:, :, 0::2, :] + H[:, :, 1::2, :]) * 0.5
    HH = (H[:, :, 0::2, :] - H[:, :, 1::2, :]) * 0.5
    return LL, LH, HL, HH


def idwt2(LL, LH, HL, HH):
    """
    2D Haar IDWT — exact inverse of dwt2.
    """
    B, C, H2, W2 = LL.shape
    L = torch.zeros(B, C, H2*2, W2, device=LL.device, dtype=LL.dtype)
    H = torch.zeros(B, C, H2*2, W2, device=LL.device, dtype=LL.dtype)
    L[:, :, 0::2, :] = LL + LH
    L[:, :, 1::2, :] = LL - LH
    H[:, :, 0::2, :] = HL + HH
    H[:, :, 1::2, :] = HL - HH
    out = torch.zeros(B, C, H2*2, W2*2, device=LL.device, dtype=LL.dtype)
    out[:, :, :, 0::2] = L + H
    out[:, :, :, 1::2] = L - H
    return out
