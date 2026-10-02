# Why you can trust (or not) a candidate

MEIDNet shows its reasoning rather than a score. Where to look:

## Before trusting the model

- **Training report → accuracy table.** A property rated *weak* means its predictions are not much better than
  guessing the mean; targets on it are unreliable.
- **Training report → alignment.** Low retrieval accuracy means property latents do not land near the right
  structures; inverse design from them is guesswork.
- **Check report → distributions.** A target in a region with almost no training data is extrapolation.

## For each candidate

- **The checklist** — every rule's measured value and allowed window. These are deterministic chemistry
  (charges, radii, distances), not model outputs.
- **The gauges** — where the prediction sits relative to the target and to the training range.
- **Warnings** — *predicted value outside the training range* (extrapolation) and *latent far from training
  latents* (the search pushed into a region the decoders never saw; predictions there are less reliable).
- **Encoder vs search** — in the Studio, compare the search's decoded prediction with the structure encoder's
  prediction for the same composition. Large disagreement is a red flag.

## For the run as a whole

- **The funnel** — which rule removed most attempts. If it is a chemical rule (charge balance, tolerance
  factor), the family's element lists may be too broad for the target; if it is *no charge-balancing element*,
  the oxidation-state tables may be missing an entry.
- **Rejected examples** — what the search *wanted* to make; often more informative than what it kept.
- **Latent map** — whether the population spread out (diversity) or collapsed.

## What MEIDNet never claims

A candidate is a *composition on an ideal prototype with model-predicted properties*. Whether it is stable,
synthesisable, or has those properties is for `meidnet screen`, DFT and the lab to decide.
