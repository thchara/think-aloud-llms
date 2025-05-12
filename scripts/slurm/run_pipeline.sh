#!/bin/zsh
#SBATCH --job-name=run_pipeline
#SBATCH --account=cocoflops
#SBATCH --partition=cocoflops
#SBATCH --nodelist=cocoflops1
#SBATCH --output=slurm-output/run_pipeline.out
#SBATCH --error=slurm-output/run_pipeline.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=48:00:00

source ~/.zshrc

cd ~/llm-verbal-protocol

conda activate verbal-protocol

python scripts/run_pipeline.py
