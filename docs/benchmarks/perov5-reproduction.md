# Perov-5: alignment across seeds

The alignment model of MEIDNet learns one space for crystal structures and their properties. This page measures how well the two modalities agree in that space, and how much the answer depends on the random seed: the same training was run seven times, and every checkpoint is public.

<div class="bench-kpis" markdown="0"><div><b>0.954 ± 0.011</b><span>cosine, 7 seeds</span></div><div><b>0.301 ± 0.034</b><span>L2, 7 seeds</span></div><div><b>86.1 ± 5.0 %</b><span>structure matching</span></div><div><b>18,928</b><span>materials</span></div></div>

[Results](#results) · [During training](#during-training) · [Unseen materials](#unseen-materials) · [Do it yourself](#do-it-yourself) · [What the runs show](perov5-insights.md)
{ .lb-toolbar }

## What was run

| | |
|---|---|
| model | early fusion of formation enthalpy and band gap; E(n)-equivariant crystal encoder; 128-dimensional latents |
| training | 2,200 epochs, batch 16, Adam, learning rate 1e-3; symmetric InfoNCE with temperature 0.01; contrastive weight raised linearly from 0 to 5 over the first 1,500 epochs (the curriculum) |
| data | all 18,928 Perov-5 materials, scored on the same materials; [unseen materials](#unseen-materials) are measured separately |
| seeds | 0 to 6, one run each, about 7 hours on one NVIDIA A100 |
| script and weights | [`reproduction/paper_alignment/`](https://github.com/ABnano/MEIDNet/blob/main/reproduction/paper_alignment) · [seven checkpoints on Hugging Face](https://huggingface.co/Babu09/MEIDNet/tree/main/reproduction) |

## Results

| seed | cosine | L2 | structure matching, sampled element | structure matching, most likely element | retrieval, top 1 |
|---|---|---|---|---|---|
| 0 | 0.9563 | 0.2934 | 90.04 % | 92.79 % | 0.245 |
| 1 | 0.9585 | 0.2862 | 91.41 % | 94.55 % | 0.288 |
| 2 | 0.9373 | 0.3529 | 82.91 % | 88.34 % | 0.218 |
| 3 | 0.9592 | 0.2839 | 91.55 % | 94.69 % | 0.249 |
| 4 | 0.9654 | 0.2615 | 78.21 % | 82.49 % | 0.267 |
| 5 | 0.9586 | 0.2863 | 85.15 % | 88.87 % | 0.215 |
| 6 | 0.9400 | 0.3449 | 83.76 % | 88.82 % | 0.127 |
| **mean ± s.d.** | **0.954 ± 0.011** | **0.301 ± 0.034** | **86.1 ± 5.0 %** | **90.1 ± 4.3 %** | **0.230 ± 0.052** |
| range | 0.937–0.965 | 0.262–0.353 | 78.2–91.5 % | 82.5–94.7 % | 0.127–0.288 |

??? info "The four measures used on this page"

    - **Cosine** and **L2**: how close the structure latent and the property latent of the same material are. Both latents
      have length one; a cosine of 1 (L2 of 0) means they coincide. They are read from the normalised encoder outputs,
      before the projection heads, which is where this model's alignment loss acts.
    - **Structure matching**: the share of materials whose crystal, decoded from the joint latent, matches the input
      according to pymatgen's `StructureMatcher` (`stol` 0.5, `angle_tol` 10, `ltol` 0.3). *Sampled element* draws the
      element of each site from the decoder's probabilities, as the training script's own evaluation does; *most likely
      element* takes the highest probability and is deterministic.
    - **Retrieval, top 1**: the share of materials whose own property vector is the nearest of all property vectors to
      their structure vector.

!!! key "A seed fixes the result"
    Seeds 0, 1, 2 were trained twice, on different hardware and library versions (torch 2.6.0, pymatgen 2024.11.13, NVIDIA A100 40 GB; torch 2.8.0, pymatgen 2025.10.7, NVIDIA A100 80 GB). Every number of the two sets is identical. The differences between the rows above therefore come from the seed alone: quote a result with its seed, or as a mean over seeds.

## During training

<div class="bench-charts" markdown="0"><div class="bench-chart" markdown="0"><p class="bench-cap">Cosine between the structure and property latents, per epoch, for the seven seeds</p><svg class="chart" viewBox="0 0 640 300" role="img" preserveAspectRatio="xMidYMid meet"><title>Cosine between the two latents during training, seven seeds</title><line class="ax" x1="52" y1="258" x2="626" y2="258"/><line class="ax" x1="52" y1="14" x2="52" y2="258"/><line class="grid" x1="73.0" y1="14" x2="73.0" y2="258"/><text class="tick" x="73.0" y="273" text-anchor="middle">0</text><line class="grid" x1="193.9" y1="14" x2="193.9" y2="258"/><text class="tick" x="193.9" y="273" text-anchor="middle">500</text><line class="grid" x1="314.7" y1="14" x2="314.7" y2="258"/><text class="tick" x="314.7" y="273" text-anchor="middle">1,000</text><line class="grid" x1="435.6" y1="14" x2="435.6" y2="258"/><text class="tick" x="435.6" y="273" text-anchor="middle">1,500</text><line class="grid" x1="556.4" y1="14" x2="556.4" y2="258"/><text class="tick" x="556.4" y="273" text-anchor="middle">2,000</text><line class="grid" x1="52" y1="250.5" x2="626" y2="250.5"/><text class="tick" x="46" y="254.5" text-anchor="end">0</text><line class="grid" x1="52" y1="191.7" x2="626" y2="191.7"/><text class="tick" x="46" y="195.7" text-anchor="end">0.25</text><line class="grid" x1="52" y1="132.8" x2="626" y2="132.8"/><text class="tick" x="46" y="136.8" text-anchor="end">0.5</text><line class="grid" x1="52" y1="73.9" x2="626" y2="73.9"/><text class="tick" x="46" y="77.9" text-anchor="end">0.75</text><line class="grid" x1="52" y1="15.1" x2="626" y2="15.1"/><text class="tick" x="46" y="19.1" text-anchor="end">1</text><text class="lab" x="339.0" y="294" text-anchor="middle">epoch</text><text class="lab" transform="translate(13,136.0) rotate(-90)" text-anchor="middle">cosine (training batches)</text><polyline class="s0" fill="none" points="73.3,243.2 73.7,229.9 74.2,241.3 74.7,227.8 75.2,215.1 75.7,211.4 76.2,212.0 76.6,210.8 77.1,208.4 77.6,205.0 78.1,200.6 78.6,198.4 79.1,195.5 79.5,193.7 80.0,189.2 80.5,186.5 81.0,183.1 81.5,179.1 82.0,175.7 82.4,170.5 82.9,165.1 83.4,160.4 83.9,155.4 84.4,151.3 84.9,146.5 85.1,143.9 87.5,122.5 89.9,106.4 92.4,94.9 94.8,86.5 97.2,79.9 99.6,75.1 102.0,70.5 104.4,67.9 106.9,64.7 109.3,63.2 111.7,60.1 114.1,57.8 116.5,54.9 118.9,52.8 121.4,50.8 123.8,49.0 126.2,47.8 128.6,46.5 131.0,44.8 133.4,43.3 135.9,43.1 138.3,41.9 140.7,41.1 143.1,40.3 145.5,39.7 147.9,40.5 150.4,38.8 152.8,38.6 155.2,37.5 157.6,37.7 160.0,38.0 162.4,36.2 164.9,36.3 167.3,35.6 169.7,35.4 181.8,33.6 193.9,34.6 205.9,31.9 218.0,31.2 230.1,30.5 242.2,30.3 254.3,29.9 266.4,28.6 278.5,28.4 290.5,28.4 302.6,28.8 314.7,27.9 326.8,27.8 338.9,27.6 351.0,27.5 363.0,26.8 375.1,27.2 387.2,26.4 399.3,26.5 411.4,27.3 423.5,26.4 435.6,26.2 447.6,25.8 459.7,25.5 471.8,26.2 483.9,26.0 496.0,25.9 508.1,25.7 520.1,25.6 532.2,25.7 544.3,25.3 556.4,25.7 568.5,25.1 580.6,25.4 592.7,25.7 604.7,25.5"/><text class="leg s0t" x="60" y="26">seed 0</text><polyline class="s1" fill="none" points="73.3,246.9 73.7,246.8 74.2,240.4 74.7,239.2 75.2,239.5 75.7,232.8 76.2,224.4 76.6,218.6 77.1,212.6 77.6,207.0 78.1,199.3 78.6,192.7 79.1,183.4 79.5,175.1 80.0,164.4 80.5,157.0 81.0,147.9 81.5,142.0 82.0,133.5 82.4,126.4 82.9,119.3 83.4,113.5 83.9,108.3 84.4,104.0 84.9,101.6 85.1,100.0 87.5,87.8 89.9,78.4 92.4,71.0 94.8,66.8 97.2,62.7 99.6,59.6 102.0,55.6 104.4,52.6 106.9,49.6 109.3,47.9 111.7,45.6 114.1,44.1 116.5,42.9 118.9,41.6 121.4,40.9 123.8,39.2 126.2,39.1 128.6,37.5 131.0,37.3 133.4,36.7 135.9,36.1 138.3,36.1 140.7,35.4 143.1,34.9 145.5,34.8 147.9,34.9 150.4,34.1 152.8,33.7 155.2,33.5 157.6,32.4 160.0,32.4 162.4,32.6 164.9,32.5 167.3,31.9 169.7,32.1 181.8,31.2 193.9,30.6 205.9,30.0 218.0,29.2 230.1,29.9 242.2,29.7 254.3,30.2 266.4,29.4 278.5,27.9 290.5,27.8 302.6,27.9 314.7,27.7 326.8,28.4 338.9,27.7 351.0,27.0 363.0,27.5 375.1,27.4 387.2,27.0 399.3,26.8 411.4,26.8 423.5,26.7 435.6,26.7 447.6,26.3 459.7,26.7 471.8,26.2 483.9,26.2 496.0,26.0 508.1,25.9 520.1,25.8 532.2,26.4 544.3,25.6 556.4,25.4 568.5,25.4 580.6,24.8 592.7,25.7 604.7,25.0"/><text class="leg s1t" x="60" y="39">seed 1</text><polyline class="s2" fill="none" points="73.3,241.1 73.7,243.7 74.2,243.0 74.7,246.3 75.2,247.1 75.7,247.4 76.2,239.7 76.6,232.9 77.1,228.2 77.6,225.0 78.1,221.1 78.6,219.8 79.1,218.7 79.5,216.3 80.0,213.7 80.5,211.1 81.0,206.9 81.5,206.3 82.0,204.4 82.4,203.9 82.9,203.3 83.4,200.4 83.9,198.9 84.4,197.4 84.9,193.5 85.1,191.8 87.5,179.5 89.9,162.1 92.4,146.0 94.8,130.1 97.2,117.7 99.6,107.8 102.0,99.1 104.4,91.8 106.9,86.2 109.3,82.1 111.7,76.8 114.1,73.2 116.5,69.4 118.9,66.5 121.4,63.4 123.8,60.4 126.2,59.0 128.6,57.1 131.0,55.8 133.4,54.3 135.9,53.3 138.3,52.8 140.7,51.4 143.1,50.4 145.5,49.4 147.9,49.0 150.4,48.1 152.8,48.2 155.2,47.8 157.6,46.8 160.0,46.4 162.4,46.2 164.9,45.5 167.3,45.0 169.7,44.3 181.8,41.9 193.9,40.3 205.9,38.6 218.0,37.8 230.1,36.2 242.2,36.0 254.3,35.7 266.4,34.7 278.5,34.2 290.5,33.7 302.6,34.2 314.7,33.5 326.8,32.6 338.9,32.0 351.0,31.9 363.0,31.5 375.1,32.1 387.2,31.1 399.3,31.2 411.4,31.4 423.5,30.7 435.6,30.6 447.6,31.4 459.7,30.4 471.8,30.2 483.9,30.1 496.0,30.1 508.1,30.5 520.1,30.5 532.2,30.0 544.3,29.8 556.4,30.4 568.5,29.6 580.6,29.5 592.7,29.8 604.7,29.5"/><text class="leg s2t" x="60" y="52">seed 2</text><polyline class="s3" fill="none" points="73.3,243.3 73.7,246.7 74.2,246.6 74.7,244.0 75.2,240.7 75.7,239.5 76.2,235.9 76.6,232.3 77.1,230.2 77.6,226.0 78.1,224.9 78.6,223.2 79.1,221.9 79.5,220.7 80.0,219.6 80.5,217.4 81.0,216.9 81.5,216.2 82.0,215.7 82.4,215.4 82.9,215.1 83.4,214.0 83.9,213.2 84.4,213.1 84.9,212.1 85.1,211.4 87.5,202.8 89.9,184.6 92.4,167.0 94.8,148.6 97.2,131.5 99.6,116.8 102.0,104.4 104.4,94.3 106.9,86.1 109.3,79.0 111.7,73.1 114.1,68.6 116.5,65.3 118.9,61.8 121.4,59.3 123.8,57.2 126.2,55.2 128.6,53.2 131.0,51.4 133.4,50.2 135.9,48.4 138.3,48.1 140.7,46.1 143.1,45.1 145.5,44.7 147.9,43.2 150.4,42.1 152.8,42.0 155.2,41.0 157.6,40.4 160.0,39.7 162.4,38.8 164.9,38.6 167.3,37.4 169.7,37.5 181.8,35.3 193.9,33.1 205.9,32.3 218.0,31.5 230.1,30.6 242.2,30.1 254.3,29.2 266.4,28.8 278.5,28.2 290.5,27.6 302.6,27.1 314.7,27.2 326.8,27.5 338.9,26.9 351.0,27.0 363.0,26.5 375.1,26.6 387.2,26.3 399.3,25.6 411.4,25.3 423.5,25.4 435.6,25.4 447.6,25.4 459.7,25.1 471.8,25.3 483.9,24.7 496.0,25.0 508.1,25.0 520.1,24.6 532.2,24.4 544.3,24.5 556.4,24.7 568.5,24.5 580.6,24.4 592.7,24.4 604.7,24.4"/><text class="leg s3t" x="60" y="65">seed 3</text><polyline class="s4" fill="none" points="73.3,236.0 73.7,242.5 74.2,235.5 74.7,239.5 75.2,239.5 75.7,241.0 76.2,240.0 76.6,236.5 77.1,233.2 77.6,232.4 78.1,227.1 78.6,214.9 79.1,203.5 79.5,192.0 80.0,176.3 80.5,160.7 81.0,148.1 81.5,134.8 82.0,124.2 82.4,114.2 82.9,106.7 83.4,99.0 83.9,92.8 84.4,86.0 84.9,81.4 85.1,79.3 87.5,66.5 89.9,60.2 92.4,57.1 94.8,54.2 97.2,51.8 99.6,49.3 102.0,47.7 104.4,45.5 106.9,44.5 109.3,42.6 111.7,41.6 114.1,40.9 116.5,39.9 118.9,39.2 121.4,38.6 123.8,37.8 126.2,37.8 128.6,36.5 131.0,36.2 133.4,35.4 135.9,34.3 138.3,33.9 140.7,34.3 143.1,34.0 145.5,34.0 147.9,32.7 150.4,32.9 152.8,32.0 155.2,32.1 157.6,32.4 160.0,32.9 162.4,32.4 164.9,32.3 167.3,32.0 169.7,32.0 181.8,31.5 193.9,30.4 205.9,29.8 218.0,28.9 230.1,28.3 242.2,28.0 254.3,27.7 266.4,27.5 278.5,26.4 290.5,26.3 302.6,26.3 314.7,26.4 326.8,25.9 338.9,25.6 351.0,25.3 363.0,24.5 375.1,24.5 387.2,24.7 399.3,23.9 411.4,24.2 423.5,24.0 435.6,24.0 447.6,23.8 459.7,24.0 471.8,23.5 483.9,23.5 496.0,23.9 508.1,23.3 520.1,23.6 532.2,23.4 544.3,23.4 556.4,23.1 568.5,23.5 580.6,23.2 592.7,23.0 604.7,24.4"/><text class="leg s4t" x="60" y="78">seed 4</text><polyline class="s0" fill="none" points="73.3,249.0 73.7,243.5 74.2,242.2 74.7,242.3 75.2,242.8 75.7,237.9 76.2,232.1 76.6,222.4 77.1,215.2 77.6,207.5 78.1,204.0 78.6,201.3 79.1,197.7 79.5,194.8 80.0,192.2 80.5,188.3 81.0,185.5 81.5,183.0 82.0,176.2 82.4,172.0 82.9,167.3 83.4,163.2 83.9,157.7 84.4,152.7 84.9,147.9 85.1,145.9 87.5,126.6 89.9,108.5 92.4,95.0 94.8,84.9 97.2,78.2 99.6,71.9 102.0,67.4 104.4,64.4 106.9,60.9 109.3,58.3 111.7,57.3 114.1,56.7 116.5,55.0 118.9,54.0 121.4,53.1 123.8,53.1 126.2,51.8 128.6,51.0 131.0,51.3 133.4,49.0 135.9,48.7 138.3,47.6 140.7,47.0 143.1,46.0 145.5,44.7 147.9,45.2 150.4,43.6 152.8,43.9 155.2,42.6 157.6,42.2 160.0,41.4 162.4,41.1 164.9,40.9 167.3,40.1 169.7,39.9 181.8,37.5 193.9,36.7 205.9,34.6 218.0,33.5 230.1,32.5 242.2,31.3 254.3,31.2 266.4,30.0 278.5,29.5 290.5,28.7 302.6,28.7 314.7,27.9 326.8,28.3 338.9,27.9 351.0,27.3 363.0,27.2 375.1,27.2 387.2,26.8 399.3,26.3 411.4,26.1 423.5,25.8 435.6,26.0 447.6,25.8 459.7,25.7 471.8,25.5 483.9,25.8 496.0,25.4 508.1,25.6 520.1,25.3 532.2,25.1 544.3,25.3 556.4,24.9 568.5,25.0 580.6,25.3 592.7,25.1 604.7,25.0"/><text class="leg s0t" x="60" y="91">seed 5</text><polyline class="s1" fill="none" points="73.3,241.6 73.7,242.0 74.2,243.6 74.7,242.7 75.2,243.1 75.7,244.7 76.2,245.7 76.6,244.7 77.1,244.1 77.6,241.4 78.1,236.4 78.6,232.2 79.1,229.7 79.5,225.1 80.0,220.0 80.5,214.8 81.0,211.0 81.5,207.3 82.0,203.9 82.4,199.3 82.9,195.4 83.4,191.6 83.9,187.5 84.4,183.1 84.9,178.2 85.1,174.3 87.5,154.6 89.9,142.9 92.4,133.1 94.8,123.3 97.2,116.1 99.6,107.5 102.0,100.3 104.4,94.5 106.9,89.9 109.3,86.1 111.7,82.0 114.1,78.7 116.5,75.9 118.9,73.1 121.4,70.5 123.8,69.1 126.2,67.6 128.6,65.8 131.0,64.0 133.4,62.6 135.9,61.6 138.3,60.9 140.7,59.5 143.1,59.4 145.5,58.4 147.9,58.0 150.4,56.2 152.8,55.4 155.2,54.1 157.6,54.2 160.0,53.6 162.4,53.1 164.9,51.8 167.3,51.2 169.7,50.2 181.8,47.7 193.9,45.2 205.9,44.1 218.0,41.0 230.1,39.9 242.2,38.7 254.3,37.2 266.4,36.7 278.5,36.2 290.5,35.2 302.6,34.6 314.7,34.2 326.8,33.6 338.9,33.7 351.0,32.6 363.0,32.1 375.1,32.2 387.2,31.8 399.3,30.8 411.4,30.6 423.5,30.5 435.6,30.3 447.6,30.0 459.7,29.6 471.8,29.8 483.9,29.2 496.0,29.2 508.1,29.4 520.1,29.3 532.2,29.1 544.3,28.8 556.4,29.6 568.5,28.5 580.6,28.5 592.7,28.8 604.7,28.8"/><text class="leg s1t" x="60" y="104">seed 6</text></svg></div></div>

The seeds differ most early in training and converge later:

| epoch | lowest seed | highest seed | spread |
|---|---|---|---|
| 10 | 0.013 | 0.159 | 0.146 |
| 25 | 0.088 | 0.285 | 0.197 |
| 50 | 0.166 | 0.727 | 0.561 |
| 100 | 0.506 | 0.844 | 0.338 |
| 200 | 0.765 | 0.900 | 0.135 |
| 400 | 0.851 | 0.928 | 0.078 |
| 800 | 0.908 | 0.947 | 0.039 |
| 1,500 | 0.934 | 0.962 | 0.028 |
| 2,200 | 0.939 | 0.960 | 0.022 |

## Unseen materials

The runs above score the materials the model was trained on. To measure materials it has never seen, the same training was repeated on 15,142 materials (80 %) with 3,786 (20 %) held out, with three seeds.

| | cosine | L2 | structure matching, sampled | structure matching, most likely | retrieval, top 1 |
|---|---|---|---|---|---|
| held-out 3,786 materials | 0.919 ± 0.006 | 0.376 ± 0.020 | 66.6 ± 5.9 % | 69.5 ± 6.3 % | 0.087–0.105 |
| the 15,142 trained on | 0.953 ± 0.008 | 0.305 ± 0.027 | 87.4 ± 4.4 % | 90.8 ± 3.9 % | 0.207–0.275 |

The alignment carries over to unseen materials with a small loss; the reconstruction of the crystal loses about twenty points. [What the runs show](perov5-insights.md#unseen) traces that loss to one cause.

## Do it yourself

=== "1 · In the browser"

    Nothing to install. The seven models are compared with the other methods on the [Perov-5 leaderboard](perov5.md#representation), and the [insights page](perov5-insights.md) has the figures behind every statement here.

=== "2 · On a laptop, about a minute"

    Recompute the cosine and L2 of any seed on a CPU. The checkpoint (2.8 MB) is downloaded once from Hugging Face to `~/.meidnet/reproduction/`.

    ```bash
    pip install git+https://github.com/ABnano/MEIDNet.git
    git clone https://github.com/ABnano/MEIDNet.git && cd MEIDNet
    meidnet download-data                                   # Perov-5 into data/perov5/
    python scripts/reproduce_alignment.py --seed 4          # prints cosine and L2
    python scripts/reproduce_alignment.py --seed 4 --structure-matching   # also rebuilds every crystal: a few minutes
    ```

    Expected for seed 4: cosine 0.9654, L2 0.2615, structure matching 82.49 % (most likely element). The values of every seed are in [`runs.csv`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/runs.csv).

=== "3 · Full training, one GPU, about 7 hours"

    The training script and its wrapper are in [`reproduction/paper_alignment/`](https://github.com/ABnano/MEIDNet/blob/main/reproduction/paper_alignment). In the clone, after `meidnet download-data`:

    ```bash
    cd reproduction/paper_alignment
    python prepare_data.py                                          # train.csv and cif_files/: all 18,928 materials
    python -u retrain_alignment.py --seed 4 --epochs 2200           # trains, then prints cosine, L2 and structure matching
    python -u retrain_alignment.py --ckpt ~/.meidnet/reproduction/meidnet_paper_rerun_seed4.pth   # evaluation only
    ```

    The same seed gives the same numbers as in the table above, on any GPU.

## Files

- [`findings.json`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/findings.json): every number on this page and the next, generated by `scripts/reproduction_findings.py`.
- [`runs.csv`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/runs.csv): one row per run. [`snapshots_seed6.csv`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/snapshots_seed6.csv): seed 6 at 29 points of training.
- [`per_material_7seeds.csv.gz`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/per_material_7seeds.csv.gz): for each of the 18,928 materials and each seed, matched or not, and the cosine.
- [Checkpoints](https://huggingface.co/Babu09/MEIDNet/tree/main/reproduction) with checksums.
