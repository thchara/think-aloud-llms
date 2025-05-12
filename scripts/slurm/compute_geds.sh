#!/bin/zsh
#SBATCH --job-name=compute_geds
#SBATCH --account=cocoflops
#SBATCH --partition=cocoflops
#SBATCH --nodelist=cocoflops2
#SBATCH --output=slurm-output/compute_geds.out
#SBATCH --error=slurm-output/compute_geds.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=48:00:00

source ~/.zshrc

cd ~/llm-verbal-protocol

conda activate verbal-protocol

python scripts/compute_geds.py --timeout 10
