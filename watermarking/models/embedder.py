import torch
import torch.nn as nn
import torch.nn.functional as F


class Embedder(nn.Module):
    """
    HVS-Adaptive Embedder — embeds in LH/HL DCT subbands.

    Key improvements over previous versions:

    1. NO direct injection (removed strength parameter).
       Direct injection was the PSNR floor — it added fixed distortion
       that loss_img could never fully remove. Equilibrium at 49.5 dB.
       Instead: signal_preservation_loss in training prevents delta collapse.

    2. HVS texture masking:
       JND (Just Noticeable Difference) theory: human eye cannot perceive
       distortion in textured regions as well as flat regions.
       T(x,y) proportional to local variance of DCT coefficients.
       Delta scaled UP in high-texture, DOWN in flat regions.
       Same perceptual distortion budget → more signal in textured areas.
       Mathematical: delta_visible = delta_raw / texture_mask
                     delta_embedded = delta_raw (but perceived as delta_visible)

    3. Separate conv heads for LH and HL.
       LH = horizontal edges (sensitive to vertical delta).
       HL = vertical edges (sensitive to horizontal delta).
       Different statistics → separate learned transforms.

    4. Signal preservation via initialization:
       Final conv initialized with small but nonzero weights
       so delta starts at ~0.3 mean abs. Training grows it naturally
       without needing direct injection crutch.
    """

    def __init__(self, max_delta: float = 5.0):
        super().__init__()
        self.max_delta = max_delta

        # Shared feature processing
        self.shared = nn.Sequential(
            nn.Conv2d(128 + 1, 128, 3, padding=1, bias=False),
            nn.GroupNorm(8, 128),
            nn.LeakyReLU(0.1),
            nn.Conv2d(128, 64, 3, padding=1, bias=False),
            nn.GroupNorm(8, 64),
            nn.LeakyReLU(0.1),
        )

        # Separate heads for LH and HL — different edge statistics
        self.head_LH = nn.Conv2d(64, 1, 3, padding=1)
        self.head_HL = nn.Conv2d(64, 1, 3, padding=1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # Init heads with small nonzero — prevents delta collapse
        # without needing direct injection
        # Target: initial delta_mean ~ 0.3 (SNR~0.01, just detectable)
        nn.init.normal_(self.head_LH.weight, mean=0.0, std=0.1)
        nn.init.normal_(self.head_HL.weight, mean=0.0, std=0.1)
        nn.init.zeros_(self.head_LH.bias)
        nn.init.zeros_(self.head_HL.bias)

    def _texture_mask(self, dct_coeff):
        """
        HVS masking: compute local variance of DCT coefficients.
        High variance = textured region = can embed more delta.

        Uses 5x5 local variance to avoid the padding size mismatch
        that caused the RuntimeError in the diagnostic test.

        Returns mask in [0.3, 4.0] — never zero (no region is invisible),
        never too large (prevent artifacts in very textured areas).
        """
        # Local mean via avg_pool with valid padding
        kernel = 5
        pad    = kernel // 2
        mu     = F.avg_pool2d(dct_coeff, kernel, stride=1, padding=pad)

        # Clamp to same spatial size (pool can add 1 pixel due to rounding)
        h, w = dct_coeff.shape[2], dct_coeff.shape[3]
        mu   = mu[:, :, :h, :w]

        # Local variance
        var  = F.avg_pool2d((dct_coeff - mu) ** 2, kernel, stride=1, padding=pad)
        var  = var[:, :, :h, :w]

        # Normalize by global mean variance — relative texture strength
        eps        = 1e-6
        var_norm   = var / (var.mean(dim=[2, 3], keepdim=True) + eps)

        # Soft mask: sqrt dampens extremes, clamp prevents overflow
        mask = torch.sqrt(var_norm + eps).clamp(0.3, 4.0)
        return mask.detach()  # mask is not differentiable — stop gradient

    def forward(self, features, LH_dct, HL_dct, watermark):
        features  = features.float()
        LH_dct    = LH_dct.float()
        HL_dct    = HL_dct.float()
        watermark = watermark.float()

        target_h, target_w = LH_dct.shape[2], LH_dct.shape[3]

        feat_up = F.interpolate(
            features, size=(target_h, target_w),
            mode='bilinear', align_corners=False)

        if watermark.dim() == 3:
            watermark = watermark.unsqueeze(1)
        if watermark.shape[1] != 1:
            watermark = watermark.mean(dim=1, keepdim=True)

        wm_resized = F.interpolate(
            watermark, size=(target_h, target_w),
            mode='bilinear', align_corners=False)

        min_b = min(feat_up.shape[0], wm_resized.shape[0])
        feat_up    = feat_up[:min_b]
        wm_resized = wm_resized[:min_b]
        LH_dct     = LH_dct[:min_b]
        HL_dct     = HL_dct[:min_b]

        # Shared feature extraction
        x        = torch.cat([feat_up, wm_resized], dim=1)
        shared   = self.shared(x)

        # Separate deltas for LH and HL
        delta_LH = self.head_LH(shared)
        delta_HL = self.head_HL(shared)

        # HVS texture masking — amplify delta where eye is less sensitive
        mask_LH  = self._texture_mask(LH_dct)
        mask_HL  = self._texture_mask(HL_dct)
        delta_LH = delta_LH * mask_LH
        delta_HL = delta_HL * mask_HL

        # Hard clamp — enforces PSNR target
        delta_LH = torch.clamp(delta_LH, -self.max_delta, self.max_delta)
        delta_HL = torch.clamp(delta_HL, -self.max_delta, self.max_delta)

        LH_mod = LH_dct + delta_LH
        HL_mod = HL_dct + delta_HL

        return LH_mod, HL_mod, delta_LH, delta_HL  # return deltas for signal loss
