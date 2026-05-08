import torch
import torch.nn as nn
import torch.nn.functional as F


class SEBlock(nn.Module):
    def __init__(self, ch, reduction=8):
        super().__init__()
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(ch, max(ch // reduction, 4), bias=False),
            nn.ReLU(),
            nn.Linear(max(ch // reduction, 4), ch, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        w = self.se(x).view(x.shape[0], x.shape[1], 1, 1)
        return x * w


class UpBlock(nn.Module):
    """
    Upsample + merge skip connection + refine.
    Skip connection provides fine-grained spatial information
    lost during encoder downsampling.
    """
    def __init__(self, in_ch, skip_ch, out_ch):
        super().__init__()
        self.up   = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch + skip_ch, out_ch, 3, padding=1, bias=False),
            nn.GroupNorm(8, out_ch),
            nn.LeakyReLU(0.1),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.GroupNorm(8, out_ch),
            nn.LeakyReLU(0.1),
            SEBlock(out_ch),
        )

    def forward(self, x, skip):
        x = self.up(x)
        # Handle size mismatch from strided conv
        if x.shape != skip.shape:
            x = F.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=False)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class Decoder(nn.Module):
    """
    U-Net style decoder with skip connections from encoder.

    Mathematical justification:
    - Watermark signal is spatially distributed in DCT domain
    - Skip connections allow decoder to correlate deep semantic
      features with shallow spatial features simultaneously
    - SE blocks learn which channels carry recoverable signal
      (critical after attacks that corrupt some channels)
    - Output: raw logits — BCEWithLogitsLoss handles sigmoid

    Architecture:
    (B,128,32,32) + skip(B,64,64,64) + skip(B,32,128,128)
         -> up1 (B,64,64,64)
         -> up2 (B,32,128,128)
         -> out (B,1,128,128) logits
    """

    def __init__(self):
        super().__init__()

        # Bottleneck refinement before upsampling
        self.bottleneck = nn.Sequential(
            nn.Conv2d(128, 128, 3, padding=1, bias=False),
            nn.GroupNorm(8, 128),
            nn.LeakyReLU(0.1),
            SEBlock(128),
        )

        self.up1 = UpBlock(in_ch=128, skip_ch=64, out_ch=64)
        self.up2 = UpBlock(in_ch=64,  skip_ch=32, out_ch=32)

        self.head = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1, bias=False),
            nn.GroupNorm(4, 16),
            nn.LeakyReLU(0.1),
            nn.Conv2d(16, 1, 1),  # 1x1 final projection
            # NO sigmoid — BCEWithLogitsLoss is AMP-safe with logits
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, features, skip2=None, skip1=None):
        """
        features : (B, 128, H/4, W/4)
        skip2    : (B, 64,  H/2, W/2)  from encoder layer1
        skip1    : (B, 32,  H,   W  )  from encoder stem
        output   : (B, 1,   H,   W  )  raw logits
        """
        x = self.bottleneck(features)

        if skip2 is not None:
            x = self.up1(x, skip2)
        else:
            x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)

        if skip1 is not None:
            x = self.up2(x, skip1)
        else:
            x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)

        return self.head(x)
