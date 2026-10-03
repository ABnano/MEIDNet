# Databases by application

Where to find training data and realistic targets: **computed** (DFT) databases give structures with properties, **experimental** databases give measured values and refined structures. MEIDNet needs, per material, one crystal structure plus one or more scalar properties ([what data do I need?](../start/what-data.md)); the last column says how far each source is from that.

Pick an application:

- [Solar cells and photovoltaics](#solar-cells-and-photovoltaics)
- [Semiconductor physics](#semiconductor-physics)
- [Batteries and ionic conductors](#batteries-and-ionic-conductors)
- [Thermoelectrics](#thermoelectrics)
- [Catalysis and surfaces](#catalysis-and-surfaces)
- [Magnetism and superconductivity](#magnetism-and-superconductivity)
- [Mechanical, dielectric and piezoelectric](#mechanical-dielectric-and-piezoelectric)
- [2D materials](#2d-materials)
- [Porous materials and MOFs](#porous-materials-and-mofs)
- [Generative-model benchmarks](#generative-model-benchmarks)
- [All databases](#all-databases)

## Solar cells and photovoltaics

**What to look for:** band gap in the 1.1-1.8 eV window (single junction) or 1.6-2.0 eV (tandem top cell), direct gap, strong absorption, formation energy / hull distance, defect tolerance, device records for the experimental side

**As MEIDNet targets:** dir_gap or any gap column + heat_all / e_above_hull; family = perovskite_abx3 (halide, oxide, chalcogenide), or your own prototype

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [OQMD](https://oqmd.org) | computed | more than 1,000,000 structures | formation energy, stability (hull), band gap (PBE), many hypothetical prototypes (Heusler, perovskite, ...) | ready: prototype-decorated entries are exactly what a MEIDNet family describes |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [NOMAD](https://nomad-lab.eu) | computed | more than 10,000,000 calculations | raw and normalised DFT outputs from many codes; band structures, DOS, energies; FAIR provenance | needs curation: pick one code and functional before building a table |
| [C2DB](https://cmr.fysik.dtu.dk/c2db/c2db.html) | computed | about 4,000 monolayers | stability (dynamic and thermodynamic), PBE / HSE / GW gaps, magnetic state, optical absorption, piezoelectric and Raman data for monolayers | ready for a 2D prototype family |
| [Cubic perovskites (CMR, Castelli et al.)](https://cmr.fysik.dtu.dk/cubic_perovskites/cubic_perovskites.html) | computed | about 19,000 ABX3 compositions | formation (heat of formation) energies and direct / indirect gaps (GLLB-SC) for cubic ABX3 with O, N, S, F anions and their mixtures - the source of Perov-5 | the published MEIDNet benchmark (Perov-5 split): meidnet download-data |
| [matminer datasets](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html) | computed + experimental | about 50 curated tables | one-line loaders for experimental band gaps (Zhuo 2018, 6,354 compounds; matbench_expt_gap 4,604), experimental formation enthalpies (Kim 2017), UCSB thermoelectrics, elastic tensors, dielectric constants, piezoelectric tensors, phonon data, superhard materials, HOIP perovskites | experimental tables are composition-only: join with a structure source (COD, Materials Project) to train; use them directly as realistic targets |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | about 300,000 inorganic structures | the reference collection of experimentally determined inorganic structures; the ground truth most DFT databases start from | structures: licence forbids redistribution, train locally |
| [Perovskite Database Project](https://www.perovskitedatabase.com) | experimental | more than 42,000 solar-cell devices | device-level records: composition, architecture, efficiency, Voc, Jsc, FF, stability, processing conditions, from the literature | no crystal structures per record: use it to choose realistic gap / composition targets and to check candidates against what has been made |
| [Hybrid organic-inorganic perovskites (Kim et al. 2017)](https://www.nature.com/articles/sdata201757) | computed | 1,346 HOIPs | DFT structures, band gaps and dielectric constants of ABX3 hybrid perovskites | ready, but organic A-site cations need a family file with molecular site groups (not shipped) |
| [Experimental band gaps (Zhuo et al. 2018)](https://pubs.acs.org/doi/10.1021/acs.jpclett.8b00124) | experimental | 6,354 compounds | measured band gaps by composition, with the matbench_expt_gap subset as a standard task | targets and validation of predicted gaps; no structures |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## Semiconductor physics

**What to look for:** band gaps at several levels of theory (PBE, HSE, mBJ) and experimental, effective masses, dielectric constants, carrier mobility proxies, band edges, phonons

**As MEIDNet targets:** gap, effective mass or dielectric constant as scalar targets; keep the level of theory consistent inside one table

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [OQMD](https://oqmd.org) | computed | more than 1,000,000 structures | formation energy, stability (hull), band gap (PBE), many hypothetical prototypes (Heusler, perovskite, ...) | ready: prototype-decorated entries are exactly what a MEIDNet family describes |
| [AFLOW](https://aflowlib.org) | computed | more than 3,500,000 entries | formation enthalpy, band gaps, elastic and thermal properties (AGL), Debye temperature, magnetic moments, prototype encyclopedia | ready; the AFLOW prototype library is a good source of family files |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [Alexandria](https://alexandria.icams.rub.de) | computed | about 4,500,000 PBE and 400,000 PBEsol / SCAN structures | formation energy, hull distance, band gap, magnetic moment, for a very large set of hypothetical compounds (1D, 2D, 3D) | ready; the usual pre-training set of generative models (MatterGen's Alex-MP-20 split) |
| [NOMAD](https://nomad-lab.eu) | computed | more than 10,000,000 calculations | raw and normalised DFT outputs from many codes; band structures, DOS, energies; FAIR provenance | needs curation: pick one code and functional before building a table |
| [Materials Cloud](https://www.materialscloud.org) | computed | curated archives (MC3D, MC2D, phonons, ...) | MC3D relaxed structures, MC2D exfoliable monolayers, phonon database, Sssp pseudopotential sets, workflow provenance (AiiDA) | ready for MC3D / MC2D tables |
| [C2DB](https://cmr.fysik.dtu.dk/c2db/c2db.html) | computed | about 4,000 monolayers | stability (dynamic and thermodynamic), PBE / HSE / GW gaps, magnetic state, optical absorption, piezoelectric and Raman data for monolayers | ready for a 2D prototype family |
| [Cubic perovskites (CMR, Castelli et al.)](https://cmr.fysik.dtu.dk/cubic_perovskites/cubic_perovskites.html) | computed | about 19,000 ABX3 compositions | formation (heat of formation) energies and direct / indirect gaps (GLLB-SC) for cubic ABX3 with O, N, S, F anions and their mixtures - the source of Perov-5 | the published MEIDNet benchmark (Perov-5 split): meidnet download-data |
| [Matbench](https://matbench.materialsproject.org) | computed | 13 tasks | standardised property-prediction tasks (band gap, formation energy, moduli, dielectric constant, ...) with fixed cross-validation folds | use the structure-based tasks as property tables |
| [matminer datasets](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html) | computed + experimental | about 50 curated tables | one-line loaders for experimental band gaps (Zhuo 2018, 6,354 compounds; matbench_expt_gap 4,604), experimental formation enthalpies (Kim 2017), UCSB thermoelectrics, elastic tensors, dielectric constants, piezoelectric tensors, phonon data, superhard materials, HOIP perovskites | experimental tables are composition-only: join with a structure source (COD, Materials Project) to train; use them directly as realistic targets |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | about 300,000 inorganic structures | the reference collection of experimentally determined inorganic structures; the ground truth most DFT databases start from | structures: licence forbids redistribution, train locally |
| [Hybrid organic-inorganic perovskites (Kim et al. 2017)](https://www.nature.com/articles/sdata201757) | computed | 1,346 HOIPs | DFT structures, band gaps and dielectric constants of ABX3 hybrid perovskites | ready, but organic A-site cations need a family file with molecular site groups (not shipped) |
| [Experimental band gaps (Zhuo et al. 2018)](https://pubs.acs.org/doi/10.1021/acs.jpclett.8b00124) | experimental | 6,354 compounds | measured band gaps by composition, with the matbench_expt_gap subset as a standard task | targets and validation of predicted gaps; no structures |
| [QMOF](https://github.com/Andrew-S-Rosen/QMOF) | computed | about 20,000 MOFs | DFT-optimised MOF structures with band gaps and charges | beyond today's cell-size limit; targets and descriptors |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## Batteries and ionic conductors

**What to look for:** ionic conductivity, migration barriers, voltage, stability window, volume change, hull distance

**As MEIDNet targets:** formation energy + conductivity (log scale) as targets; families with a mobile-ion site group

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | about 300,000 inorganic structures | the reference collection of experimentally determined inorganic structures; the ground truth most DFT databases start from | structures: licence forbids redistribution, train locally |
| [Liverpool Ionic Conductivity Database (LiIonDB)](https://pcwww.liv.ac.uk/~msd30/lmds/LiIonDatabase.html) | experimental | about 800 measurements | experimental Li-ion conductivities with temperature and the reported phase, from the literature | targets (log conductivity); join with COD / Materials Project structures |
| [Materials Project battery explorer](https://next-gen.materialsproject.org/batteries) | computed | about 4,000 intercalation electrodes | average voltage, capacity, volume change and stability of intercalation electrodes computed from the MP structures | ready: voltage and capacity as targets on the host-structure family |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## Thermoelectrics

**What to look for:** Seebeck coefficient, electrical and thermal conductivity, zT, carrier concentration and temperature; experimental data is temperature-resolved

**As MEIDNet targets:** zT or Seebeck at a fixed temperature as a scalar target

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [AFLOW](https://aflowlib.org) | computed | more than 3,500,000 entries | formation enthalpy, band gaps, elastic and thermal properties (AGL), Debye temperature, magnetic moments, prototype encyclopedia | ready; the AFLOW prototype library is a good source of family files |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [matminer datasets](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html) | computed + experimental | about 50 curated tables | one-line loaders for experimental band gaps (Zhuo 2018, 6,354 compounds; matbench_expt_gap 4,604), experimental formation enthalpies (Kim 2017), UCSB thermoelectrics, elastic tensors, dielectric constants, piezoelectric tensors, phonon data, superhard materials, HOIP perovskites | experimental tables are composition-only: join with a structure source (COD, Materials Project) to train; use them directly as realistic targets |
| [UCSB thermoelectrics (Gaultois et al.)](https://citrine.io/ucsb-te/) | experimental | about 1,100 compounds | experimental Seebeck, resistivity, thermal conductivity, zT at a given temperature | targets; join with structures |
| [Starrydata](https://www.starrydata2.org) | experimental | tens of thousands of digitised curves | temperature-dependent thermoelectric and other property curves digitised from papers | targets at a chosen temperature |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## Catalysis and surfaces

**What to look for:** adsorption energies, reaction barriers, surface energies, work functions

**As MEIDNet targets:** bulk descriptors (formation energy, d-band proxies) only - MEIDNet works on bulk prototypes, not slabs

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [NOMAD](https://nomad-lab.eu) | computed | more than 10,000,000 calculations | raw and normalised DFT outputs from many codes; band structures, DOS, energies; FAIR provenance | needs curation: pick one code and functional before building a table |
| [Open Catalyst (OC20 / OC22)](https://opencatalystproject.org) | computed | more than 1,300,000 relaxations | adsorbate-surface relaxations with energies and forces; the standard catalysis ML benchmark | surfaces are out of MEIDNet's scope; use the bulk subsets as structure sources |
| [Catalysis-Hub](https://www.catalysis-hub.org) | computed | more than 100,000 reaction energies | adsorption and reaction energies on surfaces with the DFT settings used | descriptors only |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## Magnetism and superconductivity

**What to look for:** magnetic moment and ordering, Curie / Neel temperature, superconducting Tc with the structure it belongs to

**As MEIDNet targets:** total magnetization per formula unit, Tc (log scale) as scalar targets

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [OQMD](https://oqmd.org) | computed | more than 1,000,000 structures | formation energy, stability (hull), band gap (PBE), many hypothetical prototypes (Heusler, perovskite, ...) | ready: prototype-decorated entries are exactly what a MEIDNet family describes |
| [AFLOW](https://aflowlib.org) | computed | more than 3,500,000 entries | formation enthalpy, band gaps, elastic and thermal properties (AGL), Debye temperature, magnetic moments, prototype encyclopedia | ready; the AFLOW prototype library is a good source of family files |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [Alexandria](https://alexandria.icams.rub.de) | computed | about 4,500,000 PBE and 400,000 PBEsol / SCAN structures | formation energy, hull distance, band gap, magnetic moment, for a very large set of hypothetical compounds (1D, 2D, 3D) | ready; the usual pre-training set of generative models (MatterGen's Alex-MP-20 split) |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | about 300,000 inorganic structures | the reference collection of experimentally determined inorganic structures; the ground truth most DFT databases start from | structures: licence forbids redistribution, train locally |
| [SuperCon (NIMS) and 3DSC](https://github.com/aimat-lab/3DSC) | experimental | about 16,000 Tc entries; 3DSC links 5,700 to structures | experimental superconducting critical temperatures; 3DSC matches them to ICSD / Materials Project structures | 3DSC is ready (structure + Tc); use log Tc as the target |
| [MAGNDATA (Bilbao)](https://www.cryst.ehu.es/magndata/) | experimental | about 2,000 magnetic structures | experimentally determined commensurate and incommensurate magnetic structures | structures with magnetic ordering; join with moments as targets |

## Mechanical, dielectric and piezoelectric

**What to look for:** bulk and shear moduli, hardness, dielectric tensor, piezoelectric coefficients, phonon stability

**As MEIDNet targets:** bulk modulus, dielectric constant or a piezoelectric scalar as targets

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | about 150,000 inorganic compounds | relaxed structures, formation energy, energy above hull, PBE/r2SCAN band gaps, magnetic ordering, elastic / dielectric / piezoelectric tensors, phonons for a subset, X-ray absorption, battery (intercalation) electrodes | ready: export CIFs + a property table with the API; one prototype family per table |
| [AFLOW](https://aflowlib.org) | computed | more than 3,500,000 entries | formation enthalpy, band gaps, elastic and thermal properties (AGL), Debye temperature, magnetic moments, prototype encyclopedia | ready; the AFLOW prototype library is a good source of family files |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [Materials Cloud](https://www.materialscloud.org) | computed | curated archives (MC3D, MC2D, phonons, ...) | MC3D relaxed structures, MC2D exfoliable monolayers, phonon database, Sssp pseudopotential sets, workflow provenance (AiiDA) | ready for MC3D / MC2D tables |
| [Matbench](https://matbench.materialsproject.org) | computed | 13 tasks | standardised property-prediction tasks (band gap, formation energy, moduli, dielectric constant, ...) with fixed cross-validation folds | use the structure-based tasks as property tables |
| [matminer datasets](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html) | computed + experimental | about 50 curated tables | one-line loaders for experimental band gaps (Zhuo 2018, 6,354 compounds; matbench_expt_gap 4,604), experimental formation enthalpies (Kim 2017), UCSB thermoelectrics, elastic tensors, dielectric constants, piezoelectric tensors, phonon data, superhard materials, HOIP perovskites | experimental tables are composition-only: join with a structure source (COD, Materials Project) to train; use them directly as realistic targets |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | about 300,000 inorganic structures | the reference collection of experimentally determined inorganic structures; the ground truth most DFT databases start from | structures: licence forbids redistribution, train locally |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | hundreds of datasets | a registry of published materials datasets, experimental and computed, with DOIs | a place to find and to publish tables |

## 2D materials

**What to look for:** exfoliation energy, gap, magnetic state, dynamic stability of monolayers

**As MEIDNet targets:** a 2D prototype family (e.g. MXene or TMD) with gap and exfoliation energy as targets

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | about 80,000 3D and 1,000 2D materials | OptB88vdW and TBmBJ band gaps, effective masses, dielectric functions, solar-cell efficiency (SLME), elastic tensors, piezoelectric and thermoelectric (BoltzTraP) properties, exfoliation energies, superconducting Tc (electron-phonon) for a subset | ready; the richest single source of scalar targets per structure |
| [Alexandria](https://alexandria.icams.rub.de) | computed | about 4,500,000 PBE and 400,000 PBEsol / SCAN structures | formation energy, hull distance, band gap, magnetic moment, for a very large set of hypothetical compounds (1D, 2D, 3D) | ready; the usual pre-training set of generative models (MatterGen's Alex-MP-20 split) |
| [Materials Cloud](https://www.materialscloud.org) | computed | curated archives (MC3D, MC2D, phonons, ...) | MC3D relaxed structures, MC2D exfoliable monolayers, phonon database, Sssp pseudopotential sets, workflow provenance (AiiDA) | ready for MC3D / MC2D tables |
| [C2DB](https://cmr.fysik.dtu.dk/c2db/c2db.html) | computed | about 4,000 monolayers | stability (dynamic and thermodynamic), PBE / HSE / GW gaps, magnetic state, optical absorption, piezoelectric and Raman data for monolayers | ready for a 2D prototype family |
| [2DMatPedia](http://www.2dmatpedia.org) | computed | about 6,000 monolayers | exfoliation energy, band gap, magnetic moment of monolayers derived from bulk databases | ready for a 2D prototype family |

## Porous materials and MOFs

**What to look for:** pore geometry, gas uptake, band gap of the framework, stability

**As MEIDNet targets:** frameworks exceed MEIDNet's cell-size limit today (max_sites); use the property tables to set targets and the descriptors as inspiration

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | more than 500,000 crystal structures | experimentally determined structures (organic and inorganic) as CIFs with references; no properties | structures: join with a property table to train; the natural source of experimental prototypes for family files |
| [Cambridge Structural Database (CSD)](https://www.ccdc.cam.ac.uk/solutions/software/csd/) | experimental | more than 1,300,000 organic and metal-organic structures | experimental molecular and MOF crystal structures | beyond today's cell-size limit; descriptors only |
| [QMOF](https://github.com/Andrew-S-Rosen/QMOF) | computed | about 20,000 MOFs | DFT-optimised MOF structures with band gaps and charges | beyond today's cell-size limit; targets and descriptors |
| [CoRE MOF](https://github.com/gregchung/gregchung.github.io/tree/master/CoRE-MOFs) | experimental | about 14,000 experimental MOFs | computation-ready experimental MOF structures with pore descriptors | beyond today's cell-size limit |

## Generative-model benchmarks

**What to look for:** fixed splits used by CDVAE, DiffCSP, MatterGen and MEIDNet; validity, uniqueness, novelty and stability metrics

**As MEIDNet targets:** the Perov-5 split is the published MEIDNet benchmark; MP-20 and Carbon-24 test structure representation

| database | kind | size | features | use with MEIDNet |
|---|---|---|---|---|
| [OQMD](https://oqmd.org) | computed | more than 1,000,000 structures | formation energy, stability (hull), band gap (PBE), many hypothetical prototypes (Heusler, perovskite, ...) | ready: prototype-decorated entries are exactly what a MEIDNet family describes |
| [Alexandria](https://alexandria.icams.rub.de) | computed | about 4,500,000 PBE and 400,000 PBEsol / SCAN structures | formation energy, hull distance, band gap, magnetic moment, for a very large set of hypothetical compounds (1D, 2D, 3D) | ready; the usual pre-training set of generative models (MatterGen's Alex-MP-20 split) |
| [GNoME (DeepMind)](https://github.com/google-deepmind/materials_discovery) | computed | about 380,000 stable crystals | structures predicted stable with DFT energies and hull distances; no electronic properties | structures only: join with a computed property before training |
| [Cubic perovskites (CMR, Castelli et al.)](https://cmr.fysik.dtu.dk/cubic_perovskites/cubic_perovskites.html) | computed | about 19,000 ABX3 compositions | formation (heat of formation) energies and direct / indirect gaps (GLLB-SC) for cubic ABX3 with O, N, S, F anions and their mixtures - the source of Perov-5 | the published MEIDNet benchmark (Perov-5 split): meidnet download-data |
| [CDVAE splits (Perov-5, MP-20, Carbon-24)](https://github.com/txie-93/cdvae/tree/main/data) | computed | 18,928 / 45,231 / 10,153 structures | fixed train / val / test splits used by generative-model papers; Perov-5 carries formation energy and band gap, the others energies only | ready: the format meidnet reads directly (id, cif, property columns) |

## All databases

| database | kind | access | licence | applications |
|---|---|---|---|---|
| [Materials Project](https://materialsproject.org) | computed | web, mp-api (free key) | CC BY 4.0 | Solar cells and photovoltaics, Semiconductor physics, Batteries and ionic conductors, Magnetism and superconductivity, Mechanical, dielectric and piezoelectric, Catalysis and surfaces |
| [OQMD](https://oqmd.org) | computed | web, REST API, full download | open | Solar cells and photovoltaics, Semiconductor physics, Magnetism and superconductivity, Generative-model benchmarks |
| [AFLOW](https://aflowlib.org) | computed | web, REST / AFLUX API | open | Semiconductor physics, Mechanical, dielectric and piezoelectric, Thermoelectrics, Magnetism and superconductivity |
| [JARVIS-DFT (NIST)](https://jarvis.nist.gov/jarvisdft) | computed | web, jarvis-tools (figshare downloads) | open (NIST) | Solar cells and photovoltaics, Semiconductor physics, Thermoelectrics, Mechanical, dielectric and piezoelectric, 2D materials, Magnetism and superconductivity |
| [Alexandria](https://alexandria.icams.rub.de) | computed | bulk download | CC BY 4.0 | Generative-model benchmarks, Semiconductor physics, Magnetism and superconductivity, 2D materials |
| [GNoME (DeepMind)](https://github.com/google-deepmind/materials_discovery) | computed | download | CC BY-NC 4.0 | Generative-model benchmarks |
| [NOMAD](https://nomad-lab.eu) | computed | web, API, raw calculation files | CC BY 4.0 | Semiconductor physics, Solar cells and photovoltaics, Catalysis and surfaces |
| [Materials Cloud](https://www.materialscloud.org) | computed | web, archive downloads | CC BY 4.0 (per archive) | 2D materials, Mechanical, dielectric and piezoelectric, Semiconductor physics |
| [C2DB](https://cmr.fysik.dtu.dk/c2db/c2db.html) | computed | web, ASE database download | CC BY 4.0 | 2D materials, Semiconductor physics, Solar cells and photovoltaics |
| [2DMatPedia](http://www.2dmatpedia.org) | computed | web, download | open | 2D materials |
| [Cubic perovskites (CMR, Castelli et al.)](https://cmr.fysik.dtu.dk/cubic_perovskites/cubic_perovskites.html) | computed | web, ASE database download | CC BY 4.0 | Solar cells and photovoltaics, Semiconductor physics, Generative-model benchmarks |
| [CDVAE splits (Perov-5, MP-20, Carbon-24)](https://github.com/txie-93/cdvae/tree/main/data) | computed | download (CSV with CIF column) | MIT (repository) | Generative-model benchmarks |
| [Matbench](https://matbench.materialsproject.org) | computed | web, matbench package | open | Semiconductor physics, Mechanical, dielectric and piezoelectric |
| [matminer datasets](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html) | computed + experimental | matminer.datasets.load_dataset | per dataset | Semiconductor physics, Solar cells and photovoltaics, Thermoelectrics, Mechanical, dielectric and piezoelectric |
| [Crystallography Open Database (COD)](https://www.crystallography.net/cod/) | experimental | web, full download, REST | public domain (CC0) | Semiconductor physics, Solar cells and photovoltaics, Batteries and ionic conductors, Magnetism and superconductivity, Mechanical, dielectric and piezoelectric, Porous materials and MOFs |
| [ICSD](https://icsd.products.fiz-karlsruhe.de) | experimental | licence (most universities have it) | commercial | Semiconductor physics, Solar cells and photovoltaics, Batteries and ionic conductors, Magnetism and superconductivity, Mechanical, dielectric and piezoelectric |
| [Cambridge Structural Database (CSD)](https://www.ccdc.cam.ac.uk/solutions/software/csd/) | experimental | licence | commercial (CSD-Community subset free) | Porous materials and MOFs |
| [Perovskite Database Project](https://www.perovskitedatabase.com) | experimental | web, download | CC BY 4.0 | Solar cells and photovoltaics |
| [Hybrid organic-inorganic perovskites (Kim et al. 2017)](https://www.nature.com/articles/sdata201757) | computed | download (Scientific Data), matminer | CC BY 4.0 | Solar cells and photovoltaics, Semiconductor physics |
| [Experimental band gaps (Zhuo et al. 2018)](https://pubs.acs.org/doi/10.1021/acs.jpclett.8b00124) | experimental | paper SI, matminer expt_gap | per paper | Semiconductor physics, Solar cells and photovoltaics |
| [Liverpool Ionic Conductivity Database (LiIonDB)](https://pcwww.liv.ac.uk/~msd30/lmds/LiIonDatabase.html) | experimental | web, download | open | Batteries and ionic conductors |
| [Materials Project battery explorer](https://next-gen.materialsproject.org/batteries) | computed | web, mp-api | CC BY 4.0 | Batteries and ionic conductors |
| [UCSB thermoelectrics (Gaultois et al.)](https://citrine.io/ucsb-te/) | experimental | matminer ucsb_thermoelectrics | open | Thermoelectrics |
| [Starrydata](https://www.starrydata2.org) | experimental | web, download | open | Thermoelectrics |
| [Open Catalyst (OC20 / OC22)](https://opencatalystproject.org) | computed | download, fairchem | CC BY 4.0 | Catalysis and surfaces |
| [Catalysis-Hub](https://www.catalysis-hub.org) | computed | web, GraphQL API | open | Catalysis and surfaces |
| [SuperCon (NIMS) and 3DSC](https://github.com/aimat-lab/3DSC) | experimental | NIMS MDR, 3DSC on GitHub | open (3DSC) | Magnetism and superconductivity |
| [MAGNDATA (Bilbao)](https://www.cryst.ehu.es/magndata/) | experimental | web | open | Magnetism and superconductivity |
| [QMOF](https://github.com/Andrew-S-Rosen/QMOF) | computed | download (figshare) | CC BY 4.0 | Porous materials and MOFs, Semiconductor physics |
| [CoRE MOF](https://github.com/gregchung/gregchung.github.io/tree/master/CoRE-MOFs) | experimental | download | CC BY 4.0 | Porous materials and MOFs |
| [Materials Data Facility](https://materialsdatafacility.org) | computed + experimental | web, API | per dataset | Semiconductor physics, Solar cells and photovoltaics, Batteries and ionic conductors, Thermoelectrics, Catalysis and surfaces, Mechanical, dielectric and piezoelectric |

Missing one you use? [Open an issue](https://github.com/ABnano/MEIDNet/issues) or edit `benchmarks/catalog/databases.json`.
