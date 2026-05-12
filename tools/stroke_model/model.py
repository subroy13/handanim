"""
Sketch-RNN model architecture for handwritten stroke generation.

Architecture:
  Encoder  — bidirectional LSTM over the input stroke sequence → VAE latent z
  Decoder  — unidirectional LSTM conditioned on z → Mixture Density Network (MDN)
             predicts (Δx, Δy) as a Gaussian mixture + pen state as 3-class softmax

Input representation:  (Δx, Δy, p0, p1, p2) — 5-dim per step
  p0 = pen down, p1 = pen up, p2 = end-of-sequence  (one-hot)

MDN output:  M mixture components, each with (π, μx, μy, σx, σy, ρ)
  plus 3-dim softmax for pen state q = (q0, q1, q2)

References:
  Ha & Eck (2018) "A Neural Representation of Sketch Drawings"
  https://arxiv.org/abs/1704.03477
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Hyper-parameters (defaults match the paper's "small" variant)
# ---------------------------------------------------------------------------

ENC_HIDDEN = 256   # encoder LSTM hidden size (each direction)
DEC_HIDDEN = 512   # decoder LSTM hidden size
LATENT_DIM = 128   # VAE latent z dimension
MDN_MIXTURES = 20  # number of Gaussian mixture components
INPUT_DIM = 5      # (Δx, Δy, p0, p1, p2)


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class StrokeEncoder(nn.Module):
    """Bidirectional LSTM encoder → VAE (μ, log σ²)."""

    def __init__(self, input_dim: int = INPUT_DIM, hidden: int = ENC_HIDDEN, latent: int = LATENT_DIM):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden, batch_first=True, bidirectional=True)
        # Bidirectional → 2*hidden; project to latent mean and log-variance
        self.fc_mu = nn.Linear(2 * hidden, latent)
        self.fc_logvar = nn.Linear(2 * hidden, latent)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            mu, logvar: each (batch, latent_dim)
        """
        _, (h, _) = self.lstm(x)
        # h shape: (2, batch, hidden) — concatenate both directions
        h = torch.cat([h[0], h[1]], dim=-1)  # (batch, 2*hidden)
        return self.fc_mu(h), self.fc_logvar(h)


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

class StrokeDecoder(nn.Module):
    """
    Unidirectional LSTM decoder conditioned on latent z.

    Outputs MDN parameters for (Δx, Δy) and pen state logits at each step.
    MDN output dims per step: M*(1+2+2+1) + 3 = M*6 + 3
      - π   : M mixture weights (pre-softmax)
      - μ   : M * 2  (μx, μy)
      - σ   : M * 2  (σx, σy, pre-exp)
      - ρ   : M      (correlation, pre-tanh)
      - q   : 3      (pen state logits)
    """

    def __init__(
        self,
        input_dim: int = INPUT_DIM,
        hidden: int = DEC_HIDDEN,
        latent: int = LATENT_DIM,
        mixtures: int = MDN_MIXTURES,
    ):
        super().__init__()
        self.hidden = hidden
        self.mixtures = mixtures

        # Project z to initial LSTM (h0, c0)
        self.z_to_h = nn.Linear(latent, hidden)
        self.z_to_c = nn.Linear(latent, hidden)

        # Input is concatenation of stroke step + z at every step
        self.lstm = nn.LSTMCell(input_dim + latent, hidden)

        # MDN output head
        mdn_out = mixtures * 6 + 3  # π, μx, μy, σx, σy, ρ — plus pen logits
        self.fc_out = nn.Linear(hidden, mdn_out)

    def forward(
        self,
        x: torch.Tensor,
        z: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, input_dim) — teacher-forced input sequence
            z: (batch, latent_dim)
        Returns:
            pi, mu, sigma, rho, q  — MDN parameters + pen logits
            Each has batch dimension; pi/mu/sigma/rho have mixture dimension.
        """
        batch, seq_len, _ = x.shape
        M = self.mixtures

        h = torch.tanh(self.z_to_h(z))  # (batch, hidden)
        c = torch.tanh(self.z_to_c(z))  # (batch, hidden)

        z_expand = z.unsqueeze(1).expand(-1, seq_len, -1)  # (batch, seq, latent)
        inp = torch.cat([x, z_expand], dim=-1)             # (batch, seq, input+latent)

        outputs = []
        for t in range(seq_len):
            h, c = self.lstm(inp[:, t, :], (h, c))
            outputs.append(h)

        out = self.fc_out(torch.stack(outputs, dim=1))  # (batch, seq, mdn_out)

        pi_raw  = out[..., :M]
        mu      = out[..., M: M + 2 * M].reshape(batch, seq_len, M, 2)
        sigma   = out[..., M + 2 * M: M + 4 * M].reshape(batch, seq_len, M, 2)
        rho_raw = out[..., M + 4 * M: M + 5 * M]
        q_raw   = out[..., M + 5 * M:]

        pi    = F.softmax(pi_raw, dim=-1)
        sigma = torch.exp(sigma)           # ensure positive
        rho   = torch.tanh(rho_raw)        # correlation ∈ (-1, 1)

        return pi, mu, sigma, rho, q_raw


# ---------------------------------------------------------------------------
# Full VAE model
# ---------------------------------------------------------------------------

class SketchRNN(nn.Module):
    """End-to-end Sketch-RNN VAE (encoder + decoder)."""

    def __init__(
        self,
        enc_hidden: int = ENC_HIDDEN,
        dec_hidden: int = DEC_HIDDEN,
        latent: int = LATENT_DIM,
        mixtures: int = MDN_MIXTURES,
    ):
        super().__init__()
        self.encoder = StrokeEncoder(INPUT_DIM, enc_hidden, latent)
        self.decoder = StrokeDecoder(INPUT_DIM, dec_hidden, latent, mixtures)
        self.latent_dim = latent

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Sample z ~ N(mu, sigma²) using the reparameterization trick."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(
        self,
        x_enc: torch.Tensor,
        x_dec: torch.Tensor,
    ) -> tuple:
        """
        Args:
            x_enc: encoder input  (batch, seq_len, 5)
            x_dec: decoder input  (batch, seq_len, 5) — teacher-forced, offset by 1
        Returns:
            (pi, mu, sigma, rho, q_raw, z, mu_z, logvar_z)
        """
        mu_z, logvar_z = self.encoder(x_enc)
        z = self.reparameterize(mu_z, logvar_z)
        pi, mu, sigma, rho, q_raw = self.decoder(x_dec, z)
        return pi, mu, sigma, rho, q_raw, z, mu_z, logvar_z

    @torch.no_grad()
    def sample(
        self,
        z: torch.Tensor | None = None,
        max_len: int = 200,
        temperature: float = 0.4,
        device: str = "cpu",
    ) -> list[list[list[float]]]:
        """
        Autoregressively generate a stroke sequence from latent z.

        Args:
            z: (1, latent_dim) or None to sample from prior N(0, I)
            max_len: maximum number of steps to generate
            temperature: controls randomness (lower = more deterministic)
        Returns:
            List of strokes, each stroke a list of [x, y] absolute coords.
        """
        raise NotImplementedError("TODO: implement autoregressive sampling")
