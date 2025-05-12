#!/bin/zsh
#SBATCH --job-name=code_irr_trials
#SBATCH --account=cocoflops
#SBATCH --partition=cocoflops
#SBATCH --nodelist=cocoflops1
#SBATCH --output=slurm-output/code_irr_trials.out
#SBATCH --error=slurm-output/code_irr_trials.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=96:00:00

source ~/.zshrc
cd ~/llm-verbal-protocol

conda activate verbal-protocol

python scripts/code_irr_trials.py --model_name "qwen3-235b-a22b"
