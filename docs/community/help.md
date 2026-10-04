# Getting help

**Ask PRISM**, the button at the bottom right of every page, collects the help in one place: short answers by
topic with the pages to read, a form for questions and a form for bug reports.

| You want to | Where |
|---|---|
| Ask how to do something, discuss a dataset or a result | [Discussions of the Space](https://huggingface.co/spaces/Babu09/MEIDNet/discussions) |
| Report something that does not work as documented | [GitHub issues](https://github.com/ABnano/MEIDNet/issues/new?template=bug_report.yml) |
| Submit a benchmark result | [Contribute a result](contribute.md) |

Questions are answered in public, so that the answer helps the next person with the same question. Answers that
come up repeatedly are added to the documentation.

## What to include

- What you are trying to do, what you ran or clicked, and what happened (the message, if there was one).
- The technical details that Ask PRISM fills in: the MEIDNet version, the model and its properties, the Studio
  settings (family, targets, excluded elements), the state of a training or search and the browser.

Ask PRISM sends nothing by itself. It opens Hugging Face or GitHub in a new tab with the text pre-filled, and you
can edit or delete any line before posting. Your table, structures and files are never included; if a problem
depends on them, describe the columns and a few rows, or share a small example only if you choose to.

## Common questions

**Which modalities does MEIDNet use?**
Crystal structures together with any number of scalar properties (for example a band gap, a formation enthalpy or
your own columns). Spectra such as XRD or DOS, images and text are on the [roadmap](../understand/limits.md).
See [Capabilities](../explore/capabilities.md).

**What should my dataset look like?**
One table with one row per material, a crystal structure (CIF) for each row and one numeric column per property:
[What data do I need?](../start/what-data.md) and [Bring your own dataset](../use/your-data.md).

**Why is my upload or training limited on the hosted Studio?**
The public Space is shared, so uploads, rows and epochs are capped. For larger datasets, install MEIDNet and run it
on your own computer: [5-minute quickstart](../start/quickstart.md).

**Are the predicted properties reliable?**
They are the model's estimates. Targets outside the range of the training data are extrapolations; confirm
candidates with calculations or experiments: [Interpreting a candidate](../understand/interpretability.md) and
[Screen stability with MACE](../recipes/screen.md).
