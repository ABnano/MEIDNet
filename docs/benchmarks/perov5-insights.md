# Perov-5: what the runs show

Seven training runs of the alignment model, three without the curriculum and three with materials held out give more than one number per model. This page reads them for what they say about training, about failures and about the shared space, and turns each result into something you can use. Every number is generated from [`findings.json`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/findings.json); the runs are described on [Alignment across seeds](perov5-reproduction.md).

[How the model learns](#how-the-model-learns) · [Where it fails](#where-it-fails) · [What the shared space contains](#what-the-shared-space-contains) · [In practice](#in-practice)
{ .lb-toolbar }

## How the model learns

### The curriculum builds the structures first

With the curriculum, the contrastive weight starts at zero and grows over the first 1,500 epochs. In a paired run (seed 6, the same starting weights and data order), structure matching reaches **88.3 %** at epoch 50 with the curriculum and **8.5 %** without it; without the curriculum it is still 36.2 % at epoch 300. The alignment behaves the other way round: without the curriculum the cosine is already 0.88 at epoch 10, against 0.03 with it.

<div class="bench-charts" markdown="0"><div class="bench-chart" markdown="0"><p class="bench-cap">Structure matching (most likely element), seed 6</p><svg class="chart" viewBox="0 0 460 280" role="img" preserveAspectRatio="xMidYMid meet"><title>Structure matching during the first 300 epochs, with and without the curriculum</title><line class="ax" x1="52" y1="238" x2="446" y2="238"/><line class="ax" x1="52" y1="14" x2="52" y2="238"/><line class="grid" x1="65.4" y1="14" x2="65.4" y2="238"/><text class="tick" x="65.4" y="253" text-anchor="middle">0</text><line class="grid" x1="187.4" y1="14" x2="187.4" y2="238"/><text class="tick" x="187.4" y="253" text-anchor="middle">100</text><line class="grid" x1="309.4" y1="14" x2="309.4" y2="238"/><text class="tick" x="309.4" y="253" text-anchor="middle">200</text><line class="grid" x1="431.4" y1="14" x2="431.4" y2="238"/><text class="tick" x="431.4" y="253" text-anchor="middle">300</text><line class="grid" x1="52" y1="229.7" x2="446" y2="229.7"/><text class="tick" x="46" y="233.7" text-anchor="end">0</text><line class="grid" x1="52" y1="174.4" x2="446" y2="174.4"/><text class="tick" x="46" y="178.4" text-anchor="end">25</text><line class="grid" x1="52" y1="119.1" x2="446" y2="119.1"/><text class="tick" x="46" y="123.1" text-anchor="end">50</text><line class="grid" x1="52" y1="63.7" x2="446" y2="63.7"/><text class="tick" x="46" y="67.7" text-anchor="end">75</text><text class="lab" x="249.0" y="274" text-anchor="middle">epoch</text><text class="lab" transform="translate(13,126.0) rotate(-90)" text-anchor="middle">structure matching (%)</text><polyline class="s0" fill="none" points="66.6,229.6 67.8,229.5 71.5,221.8 77.6,167.3 89.8,109.7 126.4,34.3 187.4,40.2 248.4,27.0 309.4,23.9 431.4,22.3"/><text class="leg s0t" x="60" y="26">with the curriculum</text><polyline class="s1" fill="none" points="66.6,229.7 67.8,229.7 71.5,229.2 77.6,227.4 89.8,224.5 126.4,211.0 187.4,184.6 248.4,176.8 309.4,165.0 431.4,149.7"/><text class="leg s1t" x="60" y="39">without</text></svg></div><div class="bench-chart" markdown="0"><p class="bench-cap">Cosine between the two latents, seed 6</p><svg class="chart" viewBox="0 0 460 280" role="img" preserveAspectRatio="xMidYMid meet"><title>Cosine during the first 300 epochs, with and without the curriculum</title><line class="ax" x1="52" y1="238" x2="446" y2="238"/><line class="ax" x1="52" y1="14" x2="52" y2="238"/><line class="grid" x1="65.4" y1="14" x2="65.4" y2="238"/><text class="tick" x="65.4" y="253" text-anchor="middle">0</text><line class="grid" x1="187.4" y1="14" x2="187.4" y2="238"/><text class="tick" x="187.4" y="253" text-anchor="middle">100</text><line class="grid" x1="309.4" y1="14" x2="309.4" y2="238"/><text class="tick" x="309.4" y="253" text-anchor="middle">200</text><line class="grid" x1="431.4" y1="14" x2="431.4" y2="238"/><text class="tick" x="431.4" y="253" text-anchor="middle">300</text><line class="grid" x1="52" y1="235.6" x2="446" y2="235.6"/><text class="tick" x="46" y="239.6" text-anchor="end">0</text><line class="grid" x1="52" y1="189.1" x2="446" y2="189.1"/><text class="tick" x="46" y="193.1" text-anchor="end">0.2</text><line class="grid" x1="52" y1="142.7" x2="446" y2="142.7"/><text class="tick" x="46" y="146.7" text-anchor="end">0.4</text><line class="grid" x1="52" y1="96.2" x2="446" y2="96.2"/><text class="tick" x="46" y="100.2" text-anchor="end">0.6</text><line class="grid" x1="52" y1="49.7" x2="446" y2="49.7"/><text class="tick" x="46" y="53.7" text-anchor="end">0.8</text><text class="lab" x="249.0" y="274" text-anchor="middle">epoch</text><text class="lab" transform="translate(13,126.0) rotate(-90)" text-anchor="middle">cosine</text><polyline class="s0" fill="none" points="66.6,229.7 67.8,225.9 71.5,226.1 77.6,229.4 89.8,222.3 126.4,159.7 187.4,102.1 248.4,72.0 309.4,57.5 431.4,46.1"/><text class="leg s0t" x="60" y="26">with the curriculum</text><polyline class="s1" fill="none" points="66.6,177.2 67.8,143.4 71.5,69.9 77.6,31.6 89.8,22.3 126.4,36.6 187.4,42.7 248.4,44.0 309.4,44.4 431.4,45.2"/><text class="leg s1t" x="60" y="39">without</text></svg></div></div>

After the full training, over three and seven seeds:

| | cosine | L2 | structure matching, sampled element |
|---|---|---|---|
| with the curriculum (7 seeds, 2,200 epochs) | 0.954 ± 0.011 | 0.301 ± 0.034 | 86.1 ± 5.0 % |
| without (3 seeds, 2,500 epochs) | 0.949 ± 0.009 | 0.316 ± 0.028 | 67.1 ± 7.6 % |

!!! key "What this means for you"
    The curriculum does not change how well the modalities align in the end. It decides whether the model also learns to rebuild crystals. Keep `training.contrastive_warmup_epochs` on when you train on your own data.

### Reconstruction peaks early, then swings

In the seed-6 run, structure matching is highest at epoch 300 (93.7 %), when the cosine is only 0.82. From there to the end it moves between 77.8 % and 93.7 % from one snapshot to the next, and ends at 88.5 % (cosine 0.94).

<div class="bench-charts" markdown="0"><div class="bench-chart" markdown="0"><p class="bench-cap">Structure matching and cosine over 2,200 epochs, seed 6 (29 snapshots)</p><svg class="chart" viewBox="0 0 640 280" role="img" preserveAspectRatio="xMidYMid meet"><title>Structure matching and cosine over the whole training, seed 6</title><line class="ax" x1="52" y1="238" x2="626" y2="238"/><line class="ax" x1="52" y1="14" x2="52" y2="238"/><line class="grid" x1="73.0" y1="14" x2="73.0" y2="238"/><text class="tick" x="73.0" y="253" text-anchor="middle">0</text><line class="grid" x1="193.9" y1="14" x2="193.9" y2="238"/><text class="tick" x="193.9" y="253" text-anchor="middle">500</text><line class="grid" x1="314.7" y1="14" x2="314.7" y2="238"/><text class="tick" x="314.7" y="253" text-anchor="middle">1,000</text><line class="grid" x1="435.6" y1="14" x2="435.6" y2="238"/><text class="tick" x="435.6" y="253" text-anchor="middle">1,500</text><line class="grid" x1="556.4" y1="14" x2="556.4" y2="238"/><text class="tick" x="556.4" y="253" text-anchor="middle">2,000</text><line class="grid" x1="52" y1="229.8" x2="626" y2="229.8"/><text class="tick" x="46" y="233.8" text-anchor="end">0</text><line class="grid" x1="52" y1="174.7" x2="626" y2="174.7"/><text class="tick" x="46" y="178.7" text-anchor="end">25</text><line class="grid" x1="52" y1="119.7" x2="626" y2="119.7"/><text class="tick" x="46" y="123.7" text-anchor="end">50</text><line class="grid" x1="52" y1="64.7" x2="626" y2="64.7"/><text class="tick" x="46" y="68.7" text-anchor="end">75</text><text class="lab" x="339.0" y="274" text-anchor="middle">epoch</text><polyline class="s0" fill="none" points="73.3,229.7 73.5,229.6 74.2,221.9 75.4,167.7 77.9,110.4 85.1,35.3 97.2,41.2 109.3,28.1 121.4,25.0 145.5,23.4 169.7,29.0 193.9,36.5 218.0,58.5 242.2,36.5 266.4,30.9 290.5,25.0 314.7,33.5 338.9,37.0 363.0,35.2 387.2,28.5 411.4,47.3 435.6,37.9 459.7,31.4 483.9,41.9 508.1,39.4 532.2,37.9 556.4,28.9 580.6,36.2 604.7,35.1"/><text class="leg s0t" x="60" y="26">structure matching (%)</text><polyline class="s1" fill="none" points="73.3,224.2 73.5,220.5 74.2,220.7 75.4,223.9 77.9,217.2 85.1,157.9 97.2,103.4 109.3,74.8 121.4,61.1 145.5,50.3 169.7,42.2 193.9,37.7 218.0,34.2 242.2,31.9 266.4,30.0 290.5,28.8 314.7,27.3 338.9,28.6 363.0,25.6 387.2,24.9 411.4,24.2 435.6,24.0 459.7,23.5 483.9,23.0 508.1,23.0 532.2,22.3 556.4,23.7 580.6,22.8 604.7,22.8"/><text class="leg s1t" x="60" y="39">cosine × 100</text></svg></div></div>

!!! key "What this means for you"
    The last epoch is not the best checkpoint for reconstruction. Save checkpoints during training and choose one on a validation measure. This is one seed; the swings may differ for others.

### Early alignment does not predict the final one

At epoch 50 the cosine of the seven seeds ranges from 0.17 to 0.73; at the end from 0.94 to 0.96. The order of the seeds at epoch 100 has a rank correlation of only 0.32 with their final order (figure on [Alignment across seeds](perov5-reproduction.md#during-training)).

!!! key "What this means for you"
    Do not judge a model, or stop a run, on its alignment after a few dozen epochs. A short training, such as the 30 epochs of the hosted Studio, gives a rough model whose quality depends on the seed.

### Alignment and reconstruction are independent

Across the seven seeds, the correlation between the final cosine and structure matching is 0.17 (sampled element) and 0.02 (most likely element). The seed with the highest cosine (0.965) has the lowest structure matching (78.2 %).

!!! key "What this means for you"
    Report both. A high cosine says nothing about how well crystals are rebuilt.

## Where it fails

### Failures are seed noise, not hard materials

Of the 18,928 materials, **99.94 %** are reconstructed by at least one of the seven seeds and 51.9 % by all seven; only 11 are missed by every seed. Whether one seed fails on a material says almost nothing about another seed (correlation 0.06).

<div class="bench-charts" markdown="0"><div class="bench-chart" markdown="0"><p class="bench-cap">Number of materials reconstructed by k of the seven seeds</p><svg class="chart" viewBox="0 0 460 186" role="img"><title>Materials reconstructed by k of the seven seeds</title><text class="tick" x="88" y="20" text-anchor="end">7 of 7 seeds</text><rect class="bar" x="94" y="9" width="296.0" height="14"/><text class="val" x="395.0" y="20">9,831</text><text class="tick" x="88" y="42" text-anchor="end">6 of 7 seeds</text><rect class="bar" x="94" y="31" width="188.8" height="14"/><text class="val" x="287.8" y="42">6,269</text><text class="tick" x="88" y="64" text-anchor="end">5 of 7 seeds</text><rect class="bar" x="94" y="53" width="61.5" height="14"/><text class="val" x="160.5" y="64">2,042</text><text class="tick" x="88" y="86" text-anchor="end">4 of 7 seeds</text><rect class="bar" x="94" y="75" width="15.4" height="14"/><text class="val" x="114.4" y="86">512</text><text class="tick" x="88" y="108" text-anchor="end">3 of 7 seeds</text><rect class="bar" x="94" y="97" width="5.0" height="14"/><text class="val" x="104.0" y="108">165</text><text class="tick" x="88" y="130" text-anchor="end">2 of 7 seeds</text><rect class="bar" x="94" y="119" width="2.1" height="14"/><text class="val" x="101.1" y="130">69</text><text class="tick" x="88" y="152" text-anchor="end">1 of 7 seeds</text><rect class="bar" x="94" y="141" width="1.0" height="14"/><text class="val" x="99.9" y="152">29</text><text class="tick" x="88" y="174" text-anchor="end">0 of 7 seeds</text><rect class="bar" x="94" y="163" width="1.0" height="14"/><text class="val" x="99.3" y="174">11</text></svg></div><div class="bench-chart" markdown="0"><p class="bench-cap">Right element per site, seven seeds pooled (A and B: cations; X: anions)</p><svg class="chart" viewBox="0 0 460 120" role="img"><title>Share of materials with the right element on each site</title><text class="tick" x="53" y="20" text-anchor="end">site X2</text><rect class="bar" x="59" y="9" width="331.0" height="14"/><text class="val" x="395.0" y="20">99.96 %</text><text class="tick" x="53" y="42" text-anchor="end">site X1</text><rect class="bar" x="59" y="31" width="330.8" height="14"/><text class="val" x="394.8" y="42">99.90 %</text><text class="tick" x="53" y="64" text-anchor="end">site X3</text><rect class="bar" x="59" y="53" width="330.8" height="14"/><text class="val" x="394.8" y="64">99.89 %</text><text class="tick" x="53" y="86" text-anchor="end">site A</text><rect class="bar" x="59" y="75" width="320.0" height="14"/><text class="val" x="384.0" y="86">96.65 %</text><text class="tick" x="53" y="108" text-anchor="end">site B</text><rect class="bar" x="59" y="97" width="316.1" height="14"/><text class="val" x="380.1" y="108">95.47 %</text></svg></div></div>

So several seeds can be combined. Adding the element probabilities of the seeds, site by site, and taking the most likely element gives the exact composition for **99.77 %** of the materials with three seeds and 99.99 % with seven, against 92.1 % for one seed on average (85.6–96.2 %).

!!! key "What this means for you"
    Three models trained with different seeds, with their element probabilities added, remove almost all composition errors on the training materials. It costs three trainings and no change to the model.

### The bottleneck is naming the cation

79 % of the failed reconstructions have a wrong element, and almost always on a cation site: the A site is right for 96.7 % of the materials and the B site for 95.5 %, the three anion sites for 99.9 % or more. When the composition is right, 97.8 % of the crystals match; the lattice length is off by 0.10 Å on average.

### On unseen materials the whole loss is the cation { #unseen }

| trained on 80 %, three seeds | A site right | B site right | anion sites right | match when the composition is right | lattice error |
|---|---|---|---|---|---|
| materials seen in training | 97.4 % | 97.2 % | 99.9 % | 96.2 % | 0.104 Å |
| held-out materials | 86.5 % | 84.0 % | 99.4 % | 96.0 % | 0.115 Å |

!!! key "What this means for you"
    The geometry generalises: lattice and positions are as good on unseen materials as on seen ones. What does not generalise is choosing the A and B elements. Work on the model should go there first; candidates should have their composition checked first.

### Take the most likely element

The training script's evaluation samples the element of each site. Taking the most likely element instead raises structure matching by 3.9 points on average (2.8 to 5.4 over the seven seeds).

### The decoder knows when it is unsure

Take the lowest of the five top probabilities of a decoded crystal (one per site) as its confidence. It needs no reference structure.

| confidence | share of materials (seen) | reconstructed correctly (seen) | share (held-out) | reconstructed correctly (held-out) |
|---|---|---|---|---|
| ≥ 0.9 | 77.9 % | 96.0 % | 63.7 % | 82.3 % |
| 0.6 to 0.9 | 17.6 % | 74.5 % | 26.9 % | 51.5 % |
| < 0.6 | 4.5 % | 49.0 % | 9.4 % | 34.3 % |
| all | 100 % | 90.1 % | 100 % | 69.5 % |

Area under the ROC curve: 0.81 on seen materials (seven seeds), 0.75 on held-out materials (three seeds).

!!! key "What this means for you"
    Rank or filter decoded crystals by this confidence before spending computing time on them.

### Chemistry matters little, some cations more

Structure matching by anion set, seven seeds pooled:

| anions | O₂N | ONF | O₂F | O₃ | ON₂ | O₂S | N₃ |
|---|---|---|---|---|---|---|---|
| structure matching | 91.7 % | 91.2 % | 91.0 % | 91.0 % | 89.3 % | 89.1 % | 87.2 % |

The cations with the lowest structure matching (elements with at least 100 materials):

| site | lowest | highest |
|---|---|---|
| A | Os 82 %, Cs 84 %, Ir 85 %, Rb 85 %, B 85 %, K 87 % | Sn 95 %, Bi 94 %, Sb 94 %, Ga 94 % |
| B | Ca 82 %, Hf 85 %, Mn 86 %, B 86 %, Ta 86 %, La 87 % | Cu 94 %, Ni 94 %, Sb 93 %, Ga 93 % |

## What the shared space contains

### The modalities are aligned before the projection heads

The contrastive loss of this model acts on the normalised encoder outputs. There the cosine is 0.954 ± 0.011. After the projection heads, which feed the decoder, the same pairs have a cosine of -0.978 ± 0.002: the two projected vectors point in nearly opposite directions, and the decoder reads their mean.

!!! meidnet "In the benchmark"
    The [representation task](perov5.md#representation) compares the two latents in the space where each model aligns them, declared per method. The cosine in both spaces is recorded on each method's page.

### The 128-number latents use about two directions

The participation ratio, the effective number of directions a set of vectors uses, is 2.2 ± 0.0 for the structure latents and 2.3 ± 0.1 for the property latents, out of 128; the joint latent that the decoder reads uses 8.5 ± 0.8.

!!! key "What this means for you"
    Two scalar properties can organise two directions, and the alignment pulls the structure latent onto them. A richer second modality, such as a diffraction pattern or a density of states, is the way to a richer shared space ([roadmap](../understand/limits.md)).

### The property modality of Perov-5 is thin

96.1 % of the materials (18,193) have a direct band gap of 0, and the 18,928 materials share only 903 distinct pairs of (formation enthalpy, band gap). 94 % of the materials have the same pair as at least ten others; the largest group has 261.

### Retrieval works in one direction

| | top 1 | median rank |
|---|---|---|
| from a structure, find its properties | 0.230 | 186 |
| from the properties, find the structure | 0.003 | 228 |

Ranks are among all 18,928 materials; a material sharing its properties with others is not counted against. From properties to a structure, many crystals are equally right answers.

!!! key "What this means for you"
    This is why inverse design in MEIDNet is a search and not a lookup: a material family fixes the sites, rules remove impossible compositions, and the search moves through the latent space ([How MEIDNet works](../understand/how-it-works.md)).

### Less stable materials align better and reconstruct worse

By fifths of the formation enthalpy, from the lowest to the highest:

| formation enthalpy up to (eV/atom) | 0.88 | 1.22 | 1.54 | 2.00 | 5.16 |
|---|---|---|---|---|---|
| cosine | 0.952 | 0.948 | 0.950 | 0.955 | 0.963 |
| structure matching | 91.6 % | 91.6 % | 91.2 % | 89.9 % | 86.0 % |

The correlation between a material's cosine and its formation enthalpy is 0.47 ± 0.06 over the seven seeds.

### What a structure alone predicts

On the 3,786 held-out materials, with the property of the five nearest training materials in the structure latent (three seeds):

| | formation enthalpy (eV/atom) | direct band gap (eV) |
|---|---|---|
| five nearest neighbours in the structure latent | 0.060 ± 0.004 | 0.087 ± 0.003 |
| nearest property latent (cross-modal) | 0.062 ± 0.004 | 0.131 ± 0.016 |
| linear model on the structure latent | 0.144 ± 0.015 | 0.152 ± 0.023 |
| mean of the training materials | 0.563 | 0.167 |

Mean absolute errors. The band-gap numbers are small because most gaps are zero.

!!! key "What this means for you"
    The properties decoded from the joint latent have an error of only 0.008 eV/atom, but the joint latent contains the true properties: that is a reconstruction. The error to expect for a new structure is the first row, about 0.06 eV/atom.

## In practice

What the results above suggest for anyone training or using such a model:

<div class="psteps" markdown>

1. **Keep the curriculum.** It is what teaches the model to rebuild crystals.
2. **Train three seeds, not one.** Results differ between seeds, and their errors are independent.
3. **Choose the checkpoint on a validation measure**, not at the last epoch.
4. **Decode with the most likely element**, and add the probabilities of the seeds when you have several.
5. **Rank the decoded crystals by confidence** (the lowest top probability over the sites) and check the composition first.
6. **Confirm with an MLIP, then DFT.** The [guide](perov5-guide.md) runs the first of these steps.

</div>

Steps 2, 4 and 5 are measured here on reconstruction, with the alignment model. They are not yet options of `meidnet generate`.
