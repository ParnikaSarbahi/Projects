import torch
import torch.nn as nn
import torch.nn.functional as F


class ResBlock(nn.Module):
    def __init__(self, ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(ch, ch, 3, padding=1, bias=False),
            nn.GroupNorm(8, ch),
            nn.LeakyReLU(0.1),
            nn.Conv2d(ch, ch, 3, padding=1, bias=False),
            nn.GroupNorm(8, ch),
        )
        self.act = nn.LeakyReLU(0.1)

    def forward(self, x):
        return self.act(x + self.block(x))


class SEBlock(nn.Module):
    """
    Squeeze-and-Excitation channel attention.
    Mathematically: x * sigmoid(W2 * relu(W1 * GAP(x)))
    Learns WHICH frequency channels carry watermark signal.
    Critical for decoder — watermark is spread across all DCT channels
    but only a subset carry recoverable signal after attacks.
    """
    def __init__(self, ch, reduction=8):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(ch, ch // reduction, bias=False),
            nn.ReLU(),
            nn.Linear(ch // reduction, ch, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        w = self.se(x).view(x.shape[0], x.shape[1], 1, 1)
        return x * w


class Encoder(nn.Module):
    """
    Returns intermediate feature maps for skip connections.
    Skip connections allow U-Net decoder to access both
    coarse (deep) and fine (shallow) encoder features.

    Input: (B, 2, H, W) — concatenated LH_dct, HL_dct
    Outputs:
        s1: (B, 32,  H,   W  ) — stem features
        s2: (B, 64,  H/2, W/2) — layer1 features
        out:(B, 128, H/4, W/4) — final features
    """

    def __init__(self, in_channels=2):
        super().__init__()

        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1, bias=False),
            nn.GroupNorm(4, 32),
            nn.LeakyReLU(0.1),
            ResBlock(32),
        )

        self.layer1 = nn.Sequential(
            nn.Conv2d(32, 64, 3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 64),
            nn.LeakyReLU(0.1),
            ResBlock(64),
            SEBlock(64),
        )

        self.layer2 = nn.Sequential(
            nn.Conv2d(64, 128, 3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 128),
            nn.LeakyReLU(0.1),
            ResBlock(128),
            ResBlock(128),
            SEBlock(128),
        )

    def forward(self, x):
        s1  = self.stem(x)     # (B, 32,  H,   W  )
        s2  = self.layer1(s1)  # (B, 64,  H/2, W/2)
        out = self.layer2(s2)  # (B, 128, H/4, W/4)
        return out, s2, s1     # return skips too
