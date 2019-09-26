#!/usr/bin/env python3

import os
import sys
import yaml
from snakemake.utils import read_job_properties


class SlurmScheduler:

    def __init__(self):
        self.jobscript = sys.argv[1]
        self.job_properties = read_job_properties(self.jobscript)
        self.cfg = {}
        self.load_scheduler('slurm')
        self.load_platform_settings('wally')
        self.command = ''

    def load_scheduler(self, name):
        cfg_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], f'{name}.yaml')
        self.scheduler = yaml.safe_load(open(cfg_path))

    def load_platform_settings(self, name):
        cfg_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], f'{name}.yaml')
        self.cfg[name] = yaml.safe_load(open(cfg_path))

    def check_for_setting(self, setting):
        if setting not in self.job_properties:
            return None
        else:
            return self.job_properties[setting]

    def check_for_param(self, param):
        if self.check_for_setting('params') is None:
            return None
        elif param not in self.job_properties['params']:
            return None
        else:
            return self.job_properties['params'][param]

    def generate_command(self):
        self.cmd = 'sbatch '
        for setting, arg_string in self.scheduler.items():
            value = self.check_for_setting(setting)
            if value is None:
                value = self.check_for_param(setting)
            if value is not None and value != [] and value != {}:
                if setting == 'log':
                    value = value[0]
                    dir_path = os.path.abspath(os.path.split(value)[0])
                    if not os.path.isdir(dir_path):
                        os.makedirs(dir_path)
                self.cmd += arg_string.format(*([str(value)] * arg_string.count('{}'))) + ' '
        self.cmd += f'{self.jobscript}'

    def submit_command(self):
        os.system(self.cmd)

    def submit(self):
        self.generate_command()
        self.submit_command()


if __name__ == '__main__':
    scheduler = SlurmScheduler()
    scheduler.submit()
