# lemonpie
> An open source deep learning library for Electronic Health Record (EHR) data.


In this initial release of the library ..
- it implements 2 deep learning models (an LSTM and a CNN) based on popular papers 
- that uses synthetic EHR data, created using the open source [Synthea Patient Generator](https://github.com/synthetichealth/synthea/wiki)
- to predict 4 conditions that are on the [CDC's list of top chronic diseases](https://www.cdc.gov/chronicdisease/about/costs/index.htm) that contribute most to healthcare costs

The end goal is to 
- keep adding more model implementations 
- keep adding different publicly available datasets 
- and have a leaderboard to track which models and configurations work best on these datasets

## Install

Installable lib coming soon, for now ..
1. Git clone the repo
    - `https://github.com/corazonlabs/lemonpie.git`
2. Create a new conda env using the `environment.yml` file
    - `cd lemonpie`
    - `conda env create --name lemonpie --file environment.yml`

## How to use

1. Read through and then run the following **Quick Start** guides to get a general idea. 
    - if using the cloned repo, run the noteboooks listed
    - if using installed lib, just open a jupyter notebook and copy, paste & run cell by cell from the guides
    - [Quick Walkthrough](./quick_walkthru.html) - notebook - `99_running_exps.ipynb`
    - [Running Experiments](./running_exps.html) - notebook - `99_quick_walkthru.ipynb`
2. Setup Synthea
    - Refer to [condensed instructions](./setup.html#Setup-Synthea)
    - Generate different datasets you like - e.g. 1K, 5K, 10K
3. Run experiments
    - Refer to **Detailed Docs** for customizations

## Roadmap
- **A leader-board to track which models and configurations work best on different publicly available datasets**.


- Callbacks, Mixed Precision, etc
    - Either upgrade the library to use fastai v2.
    - Or as a minimum, build functionality for fastai-style callbacks & [PyTorch AMP](https://pytorch.org/docs/stable/amp.html).

- More models
    - Pick some of the best EHR models out there and implement them.
    - **Ideas are welcome**.
- More datasets
    - eICU and MIMIC3 possibly.
    - **Ideas are welcome**.
- NLP on clinical notes
    - Synthea does not have clinical notes, so this can only be done with other datasets.
- Predicting different conditions
    - Again different datasets will allow this - e.g. hospitalization data (length of stay, in-patient mortality), ER data, etc.
- Integraion with Experiment management tools like W&B, Comet, etc,.

## Known Issues & Limitations

1. `num_workers > 0` not working yet, under investigation
    - Workaround - depending upon your GPU capacity, you can load the entire dataset on GPU pre-training with a single switch
        - If running manually set `lazy_load_gpu=False` when creating the data object with `EHRData(.... )`
        - If running through an Experiment config file, set it in the `experiment.yaml` file
2. Test coverage
    - Need to write more tests for more comprehensive coverage

## References

This library is created using the awesome [nbdev](https://nbdev.fast.ai/)

Synthea [Synthetic Patient Population Simulator](https://github.com/synthetichealth/synthea)

> Jason Walonoski, Mark Kramer, Joseph Nichols, Andre Quina, Chris Moesel, Dylan Hall, Carlton Duffett, Kudakwashe Dube, Thomas Gallagher, Scott McLachlan, Synthea:An approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record, Journal of the American Medical Informatics Association, Volume 25, Issue 3, March 2018, Pages 230–238, https://doi.org/10.1093/jamia/ocx079

LSTM Model *based on* this paper - [Scalable and accurate deep learning for electronic health records](http://arxiv.org/abs/1801.07860)

> Rajkomar, A., Oren, E., Chen, K. et al. Scalable and accurate deep learning with electronic health records. npj Digital Med 1, 18 (2018). https://doi.org/10.1038/s41746-018-0029-1

CNN Model *based* on this paper - [Deepr: A Convolutional Net for Medical Records](http://arxiv.org/abs/1607.07519)

> Nguyen, P., Tran, T., Wickramasinghe, N., & Venkatesh, S. (2017). $\mathtt {Deepr}$:A Convolutional Net for Medical Records. IEEE Journal of Biomedical and Health Informatics, 21, 22-30.
