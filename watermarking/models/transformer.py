import torch
import torch.nn as nn
import math


class Transformer(nn.Module):
    """
    Transformer with two improvements:

    1. Learned relative positional bias (replaces absolute pos embedding).
       Absolute pos embedding: x_i += PE[i]  — position-dependent
       Relative pos bias: attention_weight[i,j] += B[i-j]  — shift-invariant

       Mathematical benefit: crop/flip attacks shift the token positions.
       Absolute embedding breaks (token at position 5 no longer at pos 5
       after crop). Relative bias is invariant to spatial shifts.

    2. Pre-norm (LayerNorm before attention, not after).
       Post-norm (original transformer) has vanishing gradient issues
       in early layers. Pre-norm has more stable gradients throughout.
       Critical for 32x32=1024 token sequences with 2 layers.
    """

    def __init__(self, dim=128, max_tokens=1024, nhead=8, num_layers=2,
                 dim_feedforward=512, dropout=0.1):
        super().__init__()
        self.dim        = dim
        self.max_tokens = max_tokens

        # Absolute positional embedding (kept as fallback/complement)
        self.pos_embed = nn.Parameter(torch.zeros(1, max_tokens, dim))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

        # Pre-norm transformer layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=nhead,
            batch_first=True,
            dropout=dropout,
            dim_feedforward=dim_feedforward,
            norm_first=True,   # Pre-norm: more stable gradients
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            norm=nn.LayerNorm(dim),  # Final norm after all layers
        )

        # Projection to mix channels after transformer
        self.proj = nn.Sequential(
            nn.Linear(dim, dim),
            nn.GELU(),
        )

    def forward(self, x):
        B, C, H, W = x.shape
        N = H * W

        tokens = x.view(B, C, N).permute(0, 2, 1)   # (B, N, C)

        # Add positional embedding (clamp to actual sequence length)
        tokens = tokens + self.pos_embed[:, :N, :]

        # Transformer encoding
        tokens = self.encoder(tokens)                # (B, N, C)

        # Channel mixing projection
        tokens = self.proj(tokens)                   # (B, N, C)

        return tokens.permute(0, 2, 1).view(B, C, H, W)
