# Command line

```
meidnet init            write a starter meidnet.yaml next to your data
meidnet check  CONFIG   is my data usable?            → check_report.html
meidnet train  CONFIG   learn the latent space        → model.pt, training_report.html
meidnet generate CONFIG design candidates             → CIFs, generation_report.html
meidnet studio [CONFIG] interactive workbench in your browser
meidnet space  CONFIG   every composition of the family with rule values and predictions → CSV
meidnet demo            quick demo with the published perovskite model
meidnet screen DIR      stability screening of CIFs with MACE (optional extra)
meidnet info MODEL      describe a checkpoint
meidnet families [NAME] list / describe material families
meidnet schema          JSON Schema of the config (for editors and the Studio)
meidnet download-data   fetch the Perov-5 dataset used in the paper
```

`meidnet <command> --help` lists the options. Useful ones:

| | |
|---|---|
| `init --template perov5` | the paper's configuration instead of a blank one |
| `train --epochs N` | override `training.epochs` |
| `generate --quick` | few rounds and steps — a smoke test |
| `generate --model PATH` | use another checkpoint |
| `studio --export-static FILE.html` | self-contained Studio for a website |
| `demo --family oxide --band-gap 3 --enthalpy -0.2 -n 5` | demo targets |

If `meidnet` is not on your PATH, `python -m meidnet.cli …` is equivalent.
