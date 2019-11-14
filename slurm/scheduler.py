import logging
import os
import re
import subprocess
import sys
import time
import yaml
from collections import defaultdict
from snakemake.utils import read_job_properties


def convert_time(time):
    '''
    Utility function to convert a runtime from format 'D-HH:MM:SS' to seconds
    '''
    d, h, m, s = (int(f) for f in re.split(':|-', time))
    return ((((d * 24) + h) * 60) + m) * 60 + s


def output(cmd):
    '''
    Wrapper around subprocess.check_output that returns the output in utf-8 format
    '''
    return subprocess.check_output(cmd, shell=True).decode('utf-8')


class SlurmScheduler:

    def __init__(self):
        self.cfg = {}
        self.partitions_info = {}
        self.submission_settings = defaultdict(lambda: None)
        self.command = ''
        self.partitions_file = ''
        self.jobscript = sys.argv[1]
        self.job_properties = read_job_properties(self.jobscript)
        self.load_slurm_config()
        self.update_partitions_info()
        self.load_partitions_info()

    def load_slurm_config(self, cfg_path='slurm.yaml'):
        '''
        Loads settings from the slurm config YAML file into a dictionary.
        '''
        cfg_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], cfg_path)
        self.cfg = yaml.safe_load(open(cfg_path))
        self.partitions_file = os.path.join(os.path.split(os.path.abspath(__file__))[0], self.cfg['scheduler']['partitions_file'])

    def update_partitions_info(self):
        '''
        Retrieve information about partitions available on the cluster and store the data in a yaml file.
        This information is updated at a rate specified in the 'slurm.yaml' config file.
        Only partitions on which the user is allowed to submit are retained.
        '''
        if os.path.isfile(self.partitions_file):
            time_since_modification = time.time() - os.path.getmtime(self.partitions_file)
            if time_since_modification < self.cfg['scheduler']['partitions_update_days'] * 24 * 60 * 60:
                return  # Only update file if it's not there or it's older than update rate
        username = output('whoami').strip()  # Retrieve username
        # Retrieve slurm account
        # The command's response has format "<user>|<account>|<Admin>".
        # The account name is retrieved from the second field
        account = output(f'sacctmgr -Pn show user {username}').split('|')[1].strip()
        # Retrieve groups
        # The command's response has format "<user> : <group1> <group2> ... <groupN>"
        # The response is parsed to create a list of groups
        groups = [g for g in output(f'groups {username}')[:-1].split(':')[-1].split(' ') if g != '']
        # Retrieve and parse partition information
        # The command's response is a variable space-separated table with a header and a line per partition's
        # node configuration (CPU, memory ...). This means there are usually multiple lines for each unique partition.
        # The response is parsed to create a list in which each element is a list of values for a partition's node configuration,
        # with the first element being field names given by the header
        sinfo_response = output('sinfo --noconvert -eO "partitionname,cpus,memory,time,maxcpuspernode,groups,available,prioritytier"')
        info = [[field for field in partition[:-1].split(' ') if field != ''] for 
                partition in sinfo_response.split('\n') if partition != '']
        # Converts the list of list into a list of dictionaries, with field names given by the header as keys and settings for
        # the given partition as values.
        info = [{k: v for k, v in zip(info[0], partition)} for partition in info[1:]]
        # Final partition info format: dict with partition name as key and dict of settings as values
        summary = defaultdict(lambda: defaultdict(lambda: None))
        # Parse output from sinfo to create the final partition information summary. When there are multiple node configurations
        # for a partition, the maximum values are retained
        for partition in info:
            name = partition['PARTITION']
            # Use scontrol to get list of accounts allowed to submit to current partition
            scontrol_response = output(f'scontrol show partition {name} | grep AllowAccounts')
            allowed_accounts = re.search(r'AllowAccounts=([^\s]+)', scontrol_response).group(1)
            # Check that current user's account is allowed to submit, otherwise discards partition
            if allowed_accounts != 'ALL' and account not in allowed_accounts.split(','):
                continue
            for field, value in partition.items():
                if value.isdigit():  # For integer values, replace if current value is bigger than saved value
                    if not summary[name][field] or int(value) > summary[name][field]:
                        summary[name][field] = int(value)
                elif field == 'TIMELIMIT' and value != 'infinite':
                    duration = convert_time(value)  # Convert max runtime to seconds for easy comparison
                    if not summary[name][field] or duration > summary[name][field]:  # Replace if bigger
                        summary[name][field] = duration
                else:
                    summary[name][field] = value
        # Export summary to a yaml file
        with open(self.partitions_file, 'w') as summary_file:
            yaml.dump(dict({k: dict(v) for k, v in summary.items()}), summary_file, default_flow_style=False)

    def load_partitions_info(self):
        '''
        Load partition info YAML file generated by 'update_partitions_info' into a dictionary
        Filter out partitions blacklisted in 'slurm.yaml' config file
        '''
        self.partitions_info = yaml.safe_load(open(self.partitions_file))
        self.partitions_info = {k: v for k, v in self.partitions_info.items() if k not in self.cfg['blacklist']}

    def check_for_setting(self, setting):
        '''
        Check if a given setting is present in the job's properties (top-level setting)
        '''
        return self.job_properties[setting] if setting in self.job_properties else None

    def check_for_param(self, param):
        '''
        Check if a given setting is present in the job's parameters
        '''
        return self.job_properties['params'][param] if 'params' in self.job_properties and param in self.job_properties['params'] else None

    def check_for_resource(self, resource):
        '''
        Check if a given setting is present in the job's resources
        '''
        return self.job_properties['resources'][resource] if 'resources' in self.job_properties and resource in self.job_properties['resources'] else None

    def get_submission_settings(self):
        '''
        For each submission setting defined in the 'slurm.yaml' <options> field, check if a value is specified
        in the job's properties. First check if setting is defined in 'resources', then in 'params', and then in
        top-level settings.
        '''
        for setting, arg_string in self.cfg['options'].items():
            value = self.check_for_resource(setting)
            if value is None:
                value = self.check_for_param(setting)
            if value is None:
                value = self.check_for_setting(setting)
            if value is not None and value != [] and value != {}:
                if setting == 'log':
                    value = value[0]
                    dir_path = os.path.abspath(os.path.split(value)[0])
                    if not os.path.isdir(dir_path):
                        os.makedirs(dir_path)
                self.submission_settings[setting] = value

    def set_partition(self):
        '''
        If a partition was not manually specified by the user in the snakefile, look for the best partition
        according to the job's resources requirements. At the moment, partitions are ranked based only on PRIO_TIER,
        prioritizing partitions with higher tiers. For each partition in order of desirability, the function checks
        if the partition is up and if threads, memory, and runtime requirements can be satisfied. The first partition
        to satisfy these criteria is used. If no suitable partition is found, the function prints an error and exits.
        '''
        if self.submission_settings['partition'] is None:
            for partition, data in sorted(self.partitions_info.items(), key=lambda x: x[1]['PRIO_TIER'], reverse=True):
                suitable = True
                if data['AVAIL'] != 'up':
                    suitable = False
                elif self.submission_settings['threads'] and int(self.submission_settings['threads']) > int(data['CPUS']):
                    suitable = False
                elif self.submission_settings['memory'] and int(self.submission_settings['memory']) > int(data['MEMORY']):
                    suitable = False
                elif self.submission_settings['mem_mb'] and int(self.submission_settings['mem_mb']) > int(data['MEMORY']):
                    suitable = False
                elif self.submission_settings['runtime'] and convert_time(self.submission_settings['runtime']) > int(data['TIMELIMIT']):
                    suitable = False
                if suitable:
                    self.submission_settings['partition'] = partition
                    return
            logging.error('No partition was found to satisfy resources requirements')
            exit(1)
        elif self.submission_settings['partition'] not in self.partitions_info:
            logging.error(f'Partition <{self.submission_settings["partition"]}> specified by user was not found')
            exit(1)

    def generate_command(self):
        '''
        Generate the submission command based on submission settings.
        '''
        self.command = 'sbatch '
        for setting, arg_string in self.cfg['options'].items():
            if self.submission_settings[setting] is not None:
                self.command += arg_string.format(*([str(self.submission_settings[setting])] * arg_string.count('{}'))) + ' '
        self.command += f'{self.jobscript}'

    def submit_command(self):
        '''
        Submit the command and parse response to output only the submission id, which is required by Snakemake to check
        the job's status.
        '''
        submit_response = subprocess.run(self.command, check=True, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
        submit_regex = re.search(r'Submitted batch job (\d+)', submit_response)
        print(submit_regex.group(1))

    def submit(self):
        '''
        Top-level function handling all steps of the submission process.
        '''
        self.get_submission_settings()
        self.set_partition()
        self.generate_command()
        self.submit_command()
