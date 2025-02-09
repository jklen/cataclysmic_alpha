#!/bin/bash

# Activate Mamba environment
source ~/miniforge3/etc/profile.d/conda.sh
conda activate py310_calpha
cd /home/jk/projects/cataclysmic_alpha/scripts

# Run the Python script
python run_portfolio.py -c "../configs/portfolios_hhhl_ml1_200.yaml"
#python ~/projects/cataclysmic_alpha/experiment_scripts/print_datetime.py -c "KOK"