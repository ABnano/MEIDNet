"""
MEIDNet — Multimodal Equivariant Inverse Design Network
==========================================================
Property-conditioned constrained inverse design for cubic ABX3 perovskites.

Public API
----------
    from meidnet.model import (
        DualAutoencoderModel,
        SE3Encoder, SE3Decoder,
        PropertyEncoder, PropertyDecoder,
        TripleModalityDataset,
        contrastive_loss, reconstruction_loss,
    )

    # Design module is invoked as a CLI via scripts/generate_candidates.py
    # or called directly: python meidnet/design.py --help
"""

__version__ = "1.0.0"
__author__  = "MEIDNet Contributors"
