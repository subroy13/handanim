"""
Training script for the Sketch-RNN stroke model.

Usage:
  python train.py --dataset dataset.npz --epochs 100 --output checkpoints/

The script saves a checkpoint after every epoch and keeps the best val-loss
checkpoint as checkpoints/best.pt.

KL annealing:
  The KL weight η is annealed from 0 → 1 over the first `kl_anneal_steps`
  gradient steps, following the schedule from Ha & Eck (2018):
    η_t = 1 - (1 - η_min) * R^t

Gradient clipping:
  Gradients are clipped to `grad_clip` (default 1.0) before every step.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from model import SketchRNN


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class StrokeDataset(Dataset):
    """Loads variable-length stroke sequences from a .npz file."""

    def __init__(self, sequences: list[np.ndarray], max_len: int = 200):
        self.sequences = sequences
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            x_enc: (max_len, 5) encoder input (padded)
            x_dec: (max_len, 5) decoder input (shifted by 1, prepended with SOS)
        """
        raise NotImplementedError("TODO: pad/truncate sequence, one-hot pen state, build enc/dec split")


def collate_fn(batch: list[tuple[torch.Tensor, torch.Tensor]]) -> tuple[torch.Tensor, torch.Tensor]:
    """Stack variable-length sequences into a batch (they are already padded)."""
    enc = torch.stack([b[0] for b in batch])
    dec = torch.stack([b[1] for b in batch])
    return enc, dec


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------

def mdn_loss(
    pi: torch.Tensor,
    mu: torch.Tensor,
    sigma: torch.Tensor,
    rho: torch.Tensor,
    target_xy: torch.Tensor,
) -> torch.Tensor:
    """
    Negative log-likelihood of target_xy under the bivariate Gaussian mixture.

    Args:
        pi:        (batch, seq, M)       mixture weights
        mu:        (batch, seq, M, 2)    means (μx, μy)
        sigma:     (batch, seq, M, 2)    std devs (σx, σy) — already exp'd
        rho:       (batch, seq, M)       correlations — already tanh'd
        target_xy: (batch, seq, 2)       ground-truth (Δx, Δy)
    """
    raise NotImplementedError("TODO: compute bivariate Gaussian NLL over mixture components")


def pen_loss(q_raw: torch.Tensor, target_pen: torch.Tensor) -> torch.Tensor:
    """Cross-entropy loss over the 3-class pen state."""
    batch, seq, _ = q_raw.shape
    return nn.functional.cross_entropy(
        q_raw.reshape(batch * seq, 3),
        target_pen.reshape(batch * seq).long(),
    )


def kl_loss(mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
    """KL divergence from posterior N(mu, sigma²) to prior N(0, I)."""
    return -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())


def kl_weight(step: int, anneal_steps: int = 10_000, eta_min: float = 0.01, R: float = 0.99999) -> float:
    """KL annealing schedule from Ha & Eck (2018)."""
    return 1.0 - (1.0 - eta_min) * (R ** step)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(args: argparse.Namespace):
    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    print(f"Device: {device}")

    # Load dataset
    data = np.load(args.dataset, allow_pickle=True)
    train_set = StrokeDataset(list(data["train"]), max_len=args.max_len)
    val_set   = StrokeDataset(list(data["val"]),   max_len=args.max_len)

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True,  collate_fn=collate_fn)
    val_loader   = DataLoader(val_set,   batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)

    model = SketchRNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.9999)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    best_val_loss = math.inf
    global_step = 0

    for epoch in range(1, args.epochs + 1):
        # --- train ---
        model.train()
        train_loss = 0.0
        for x_enc, x_dec in train_loader:
            x_enc, x_dec = x_enc.to(device), x_dec.to(device)

            pi, mu, sigma, rho, q_raw, _, mu_z, logvar_z = model(x_enc, x_dec)

            # TODO: extract target_xy and target_pen from x_dec
            target_xy  = x_dec[..., :2]       # placeholder
            target_pen = x_dec[..., 2].long()  # placeholder

            loss_r = mdn_loss(pi, mu, sigma, rho, target_xy) + pen_loss(q_raw, target_pen)
            loss_kl = kl_loss(mu_z, logvar_z)
            eta = kl_weight(global_step, args.kl_anneal_steps)
            loss = loss_r + eta * loss_kl

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()
            global_step += 1

        train_loss /= len(train_loader)

        # --- validate ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_enc, x_dec in val_loader:
                x_enc, x_dec = x_enc.to(device), x_dec.to(device)
                pi, mu, sigma, rho, q_raw, _, mu_z, logvar_z = model(x_enc, x_dec)
                target_xy  = x_dec[..., :2]
                target_pen = x_dec[..., 2].long()
                loss_r  = mdn_loss(pi, mu, sigma, rho, target_xy) + pen_loss(q_raw, target_pen)
                loss_kl = kl_loss(mu_z, logvar_z)
                val_loss += (loss_r + loss_kl).item()
        val_loss /= len(val_loader)

        print(f"Epoch {epoch:03d}  train={train_loss:.4f}  val={val_loss:.4f}  η={eta:.4f}")

        # Save checkpoint
        checkpoint = {"epoch": epoch, "model": model.state_dict(), "optimizer": optimizer.state_dict()}
        torch.save(checkpoint, output_dir / f"epoch_{epoch:03d}.pt")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(checkpoint, output_dir / "best.pt")
            print(f"  → New best ({best_val_loss:.4f}), saved checkpoints/best.pt")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Sketch-RNN stroke model.")
    parser.add_argument("--dataset",         required=True,          help=".npz file from preprocess.py")
    parser.add_argument("--output",          default="checkpoints",  help="Directory for checkpoints")
    parser.add_argument("--epochs",          type=int, default=100)
    parser.add_argument("--batch-size",      type=int, default=128)
    parser.add_argument("--lr",              type=float, default=1e-3)
    parser.add_argument("--max-len",         type=int, default=200,  help="Truncate/pad sequences to this length")
    parser.add_argument("--grad-clip",       type=float, default=1.0)
    parser.add_argument("--kl-anneal-steps", type=int, default=10_000)
    args = parser.parse_args()

    train(args)
