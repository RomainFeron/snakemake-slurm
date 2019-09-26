# Snakemake profile for Slurm schedulers

This profile is heavily inspired from the Slurm profile in Snakemake's official profiles [repository](https://github.com/Snakemake-Profiles/slurm). The main differences at the moment are no cookiecutter dependency, simpler and cleaner implementation, and better documentation and usability. The main planned feature is a smart handling of slurm partitions based on job requirements.
