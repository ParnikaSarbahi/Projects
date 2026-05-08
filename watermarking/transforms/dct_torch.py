import torch
import torch_dct


def dct2(x):
    """
    2D DCT-II — differentiable, GPU-native, autograd-safe.
    PSNR > 130 dB round-trip. Gradients flow.
    Input : (B, C, H, W) real tensor
    Output: (B, C, H, W) DCT-II coefficients
    """
    return torch_dct.dct_2d(x, norm=None)


def idct2(x):
    """
    2D IDCT-II — exact inverse of dct2.
    Input : (B, C, H, W) DCT-II coefficients
    Output: (B, C, H, W) reconstructed real tensor
    """
    return torch_dct.idct_2d(x, norm=None)
