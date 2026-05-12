"""
Export the trained Sketch-RNN decoder to ONNX and upload to Hugging Face Hub.

Only the decoder is exported — at inference time we sample z from the prior
N(0, I) so the encoder is not needed.

Usage:
  # Export to ONNX only
  python export.py --checkpoint checkpoints/best.pt --output stroke_model.onnx

  # Export and push to Hugging Face Hub
  python export.py --checkpoint checkpoints/best.pt --output stroke_model.onnx \\
                   --hf-repo subroy13/handanim-stroke-model --hf-token $HF_TOKEN

ONNX inputs:
  x_step  — (1, 1, 5)        current stroke step
  z       — (1, latent_dim)  latent vector
  h       — (1, dec_hidden)  LSTM hidden state
  c       — (1, dec_hidden)  LSTM cell state

ONNX outputs:
  pi, mu, sigma, rho  — MDN parameters for (Δx, Δy)
  q_raw               — pen state logits (3-class)
  h_next, c_next      — updated LSTM states
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from model import LATENT_DIM, DEC_HIDDEN, INPUT_DIM, MDN_MIXTURES, SketchRNN


# ---------------------------------------------------------------------------
# ONNX-compatible decoder wrapper
# ---------------------------------------------------------------------------

class DecoderStep(torch.nn.Module):
    """
    Single-step wrapper around StrokeDecoder for ONNX export.

    The ONNX graph runs one LSTMCell step at a time, with explicit h/c
    state threading — this makes the autoregressive sampling loop expressible
    in onnxruntime without dynamic control flow.
    """

    def __init__(self, model: SketchRNN):
        super().__init__()
        self.decoder = model.decoder

    def forward(
        self,
        x_step: torch.Tensor,   # (1, 1, input_dim)
        z: torch.Tensor,        # (1, latent_dim)
        h: torch.Tensor,        # (1, dec_hidden)
        c: torch.Tensor,        # (1, dec_hidden)
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Returns (pi, mu, sigma, rho, q_raw, h_next, c_next)."""
        raise NotImplementedError("TODO: implement single-step forward through LSTMCell + fc_out")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def load_model(checkpoint_path: str | Path, device: torch.device) -> SketchRNN:
    model = SketchRNN()
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model.to(device)


def export_onnx(model: SketchRNN, output_path: str | Path, device: torch.device):
    """Trace DecoderStep and export to ONNX with named dynamic axes."""
    wrapper = DecoderStep(model).to(device)
    wrapper.eval()

    # Dummy inputs (batch=1, seq=1)
    dummy_x     = torch.zeros(1, 1, INPUT_DIM,   device=device)
    dummy_z     = torch.zeros(1, LATENT_DIM,     device=device)
    dummy_h     = torch.zeros(1, DEC_HIDDEN,     device=device)
    dummy_c     = torch.zeros(1, DEC_HIDDEN,     device=device)

    torch.onnx.export(
        wrapper,
        (dummy_x, dummy_z, dummy_h, dummy_c),
        str(output_path),
        input_names=["x_step", "z", "h", "c"],
        output_names=["pi", "mu", "sigma", "rho", "q_raw", "h_next", "c_next"],
        dynamic_axes={
            "x_step": {0: "batch"},
            "z":      {0: "batch"},
            "h":      {0: "batch"},
            "c":      {0: "batch"},
        },
        opset_version=17,
        do_constant_folding=True,
    )
    print(f"Exported ONNX model → {output_path}")


def verify_onnx(onnx_path: str | Path):
    """Quick sanity-check: load with onnxruntime and run a dummy forward pass."""
    import onnxruntime as ort
    import numpy as np

    sess = ort.InferenceSession(str(onnx_path))
    dummy = {
        "x_step": np.zeros((1, 1, INPUT_DIM),  dtype=np.float32),
        "z":      np.zeros((1, LATENT_DIM),     dtype=np.float32),
        "h":      np.zeros((1, DEC_HIDDEN),     dtype=np.float32),
        "c":      np.zeros((1, DEC_HIDDEN),     dtype=np.float32),
    }
    outputs = sess.run(None, dummy)
    print(f"ONNX verification passed — {len(outputs)} output tensors")
    for name, arr in zip(sess.get_outputs(), outputs, strict=False):
        print(f"  {name.name}: {arr.shape}")


def upload_to_hub(onnx_path: str | Path, repo_id: str, token: str):
    """Push the ONNX file to a Hugging Face Hub model repository."""
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=repo_id, token=token, repo_type="model", exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(onnx_path),
        path_in_repo="stroke_model.onnx",
        repo_id=repo_id,
        token=token,
        commit_message="Upload ONNX stroke model",
    )
    print(f"Uploaded → https://huggingface.co/{repo_id}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Sketch-RNN decoder to ONNX.")
    parser.add_argument("--checkpoint", required=True, help="Path to best.pt checkpoint")
    parser.add_argument("--output",     default="stroke_model.onnx", help="Output .onnx path")
    parser.add_argument("--verify",     action="store_true", help="Run onnxruntime verification after export")
    parser.add_argument("--hf-repo",    default=None, help="HF Hub repo ID, e.g. subroy13/handanim-stroke-model")
    parser.add_argument("--hf-token",   default=None, help="HF Hub write token (or set HF_TOKEN env var)")
    args = parser.parse_args()

    device = torch.device("cpu")  # always export on CPU for portability
    model = load_model(args.checkpoint, device)
    export_onnx(model, args.output, device)

    if args.verify:
        verify_onnx(args.output)

    if args.hf_repo:
        import os
        token = args.hf_token or os.environ.get("HF_TOKEN")
        if not token:
            raise ValueError("Provide --hf-token or set the HF_TOKEN environment variable.")
        upload_to_hub(args.output, args.hf_repo, token)
