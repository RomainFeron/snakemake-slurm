#!/usr/bin/env python3

'''
Submission script for Snakemake.
The entire submission process is handled by the SlurmScheduler object.
'''

import logging
from scheduler import SlurmScheduler

if __name__ == '__main__':

    # Setup logging
    logging.basicConfig(level=logging.INFO,
                        format='[slurm-submit]::[%(asctime)s]::%(levelname)s  %(message)s',
                        datefmt='%Y.%m.%d - %H:%M:%S')

    scheduler = SlurmScheduler()
    scheduler.submit()
