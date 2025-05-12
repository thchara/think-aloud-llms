#!/bin/zsh
#SBATCH --job-name=batch_coding
#SBATCH --account=cocoflops
#SBATCH --partition=cocoflops
#SBATCH --nodelist=cocoflops2
#SBATCH --output=slurm-output/batch_coding.out
#SBATCH --error=slurm-output/batch_coding.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=96:00:00

source ~/.zshrc
cd ~/llm-verbal-protocol

conda activate verbal-protocol

python code/preproc/code_with_lm_batched.py
