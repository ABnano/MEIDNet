# Paper

**MEIDNet: Multimodal generative AI framework for inverse materials design.**
Anand Babu, Rogério Almeida Gouvêa, Pierre Vandergheynst, Gian-Marco Rignanese.
*npj Computational Materials* (2026). [doi:10.1038/s41524-026-02153-3](https://www.nature.com/articles/s41524-026-02153-3) ·
[arXiv:2601.22009](https://arxiv.org/abs/2601.22009)

```bibtex
@article{meidnet2026,
  title   = {MEIDNet: Multimodal generative AI framework for inverse materials design},
  author  = {Anand Babu and Rog{\'e}rio Almeida Gouv{\^e}a and Pierre Vandergheynst and Gian-Marco Rignanese},
  journal = {npj Computational Materials},
  year    = {2026},
  doi     = {10.1038/s41524-026-02153-3}
}
```

## Code and data of the paper

- Code as published: tag [`v1.0.0-paper`](https://github.com/ABnano/MEIDNet/releases/tag/v1.0.0-paper)
  (frozen; MEIDNet 2 reproduces it bit for bit — see [Perov-5](../examples/perov5.md)).
- Checkpoints: `checkpoints/` in the repository (2.8 MB each).
- Data: Perov-5 in the CDVAE split (`meidnet download-data`); Castelli et al., *Energy Environ. Sci.* 5, 5814 (2012);
  Xie et al., *ICLR* (2022).
- Generated structures: `examples/perov5/paper_results/`.

## Related

- Satorras, Hoogeboom, Welling, *E(n) equivariant graph neural networks*, ICML 2021 (the encoder).
- Radford et al., *CLIP*, ICML 2021 (the alignment objective).
- Batatia et al., *MACE-MP-0* (stability screening).
