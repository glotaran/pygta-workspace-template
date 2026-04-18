# quickstart

Quickstart example using pyglotaran simulated sequential spectral decay data

## Experiment Goal

Demonstrate the end-to-end pyglotaran workflow using the built-in simulated
sequential spectral decay dataset. No external data files required.

## Data Provenance

Dataset is generated programmatically from
`glotaran.testing.simulated_data.sequential_spectral_decay.DATASET`.
It simulates a 3-compartment sequential decay (s1 → s2 → s3) with a Gaussian IRF.

## Models

- `models/model.yaml` — 3-compartment sequential decay with Gaussian IRF (`irf1`)
- `models/parameters.yaml` — initial guesses: kinetic rates [0.51, 0.31, 0.11],
  IRF center 0.31 ns, IRF width 0.11 ns

Best fit: `models/parameters.yaml` (starting parameters recover the simulation truth).
