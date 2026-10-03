# Distribution: the same release on other platforms

Everything here points at the single source of truth, the GitHub repository and its releases.

| platform | what | how |
|---|---|---|
| Hugging Face | model repo `Babu09/MEIDNet` (checkpoints + model card), Space `Babu09/MEIDNet` (MEIDNet Prism) | `python app/deploy_docker_space.py --repo Babu09/MEIDNet`; the model card is `distribution/hf_model_card.md` |
| Zenodo | a DOI per GitHub release (software archive) | on zenodo.org, GitHub integration: switch on `ABnano/MEIDNet`; every `gh release create vX.Y.Z` is archived; metadata comes from `.zenodo.json` |
| Kaggle | a dataset with the checkpoints and the config | `pip install kaggle`, put your API token in `~/.kaggle/kaggle.json`, then `python distribution/kaggle_bundle.py` and `kaggle datasets create -p build/kaggle` (metadata: `distribution/kaggle/dataset-metadata.json`) |
| Science Data Bank (scidb.cn) | the same bundle as a data record | upload `build/kaggle/*` through the web form, cite the paper DOI as the related publication |
| GitHub | releases with the checkpoint bundle and the tour video | `gh release create vX.Y.Z build/release/*` |

`CITATION.cff` in the repository root gives GitHub its "Cite this repository" button.
