#!/bin/bash

#SBATCH --job-name 
#SBATCH --output slurm-%j.out
#SBATCH --nodes=1
pwd; hostname; date
#SBATCH --ntasks=30
#SBATCH --mem-per-cpu=3000MB
#SBATCH --cpus-per-task=1
