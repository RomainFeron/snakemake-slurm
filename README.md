# Snakemake profile for Slurm schedulers

This profile is heavily inspired from the Slurm profile in Snakemake's official profiles [repository](https://github.com/Snakemake-Profiles/slurm). This profile is great, but I was not entirely happy with some of its features. That's why I've implemented this SLURM profile with the following features:
- No cookiecutter dependency
- Comprehensive documentation making the profile easy to use
- "Smart" handling of partitions
- Customability through YAML files
- "Clean" implementation to allow adding new features efficiently

## Installation

```bash
git clone https://github.com/RomainFeron/snakemake-slurm.git
./INSTALL
```

By default, the profile will be installed to `~/.config/snakemake/slurm`. You can specify a different name for the profile by running `./INSTALL <profile_name>`; then, the profile will be installed in `~/.config/snakemake/<profile_name>`.

## Usage

### Using the profile

To use this profile when running snakemake, use the Snakemake runtime parameter `--profile slurm` (replace `slurm` with `<profile_name>` if you installed the profile under a different name). For more information on using Snakemake profile, check the [official Snakemake documentation](https://snakemake.readthedocs.io/en/latest/executable.html#profiles).

### Specifying parameter values

The profile will check Snakemake's jobscript for all parameters defined in the `options` field of the file `slurm.yaml`. By default, these parameters are:

| Option | Description | Snakemake keyword |
|---|---|---|
| threads | Number of CPUs to request at submission | `threads` |
| memory | Maximum memory to request at submission (**in Mb**) | `resources: memory`<br>`params: memory`|
| runtime | Maximum runtime to request at submission (**format: "D-HH:MM:SS"**) | `params: runtime`|
| log | Path to log file | `log` |
| partition | Partition to submit the job to | `params: partition`|

For instance a rule requiring 8 threads, 4 days runtime, and 16 Gb of memory will look like:

```python
rule example:
    output: 'example.txt'
    threads: 8
    params:
        runtime: '4-00:00:00'
    resources:
        memory: 16000
    shell:
    'echo "example" > example.txt'
```

**Note :** it is advised to specify memory with the `resources` keyword, as it allows Snakemake to resubmit the job with higher memory requirements in case of failure.

You can implement additional parameters by adding an entry to the `options` field of the file `slurm.yaml`, with format:
```yaml
options:
    <option_name>: <slurm flag>={}
```
In this case, `<option_name>` should match the name of the Snakemake rule option, and `<slurm_flag>` is the flag used to specify this option with the `sbatch` command. The `{}` will be substituted by the option's value if it has been specified in the Snakemake rule.

In the Snakemake rule, options can be specified either at the rule's level (*e.g.* threads), within the `params` keyword, or within the `resources` keyword. The profile will first look for the option in `resources`, then `params`, then at the rule's level.

### Blacklisting partitions

The profile automatically detects all partitions available on the cluster and selects the one with highest priority that satisfies the resources requirements. If you do not want Snakemake to submit to specific partitions at all, you can specify these partitions in the `blacklist` field of the file `slurm.yaml`.

**Example**:
```yaml
blacklist:
    - long
```

### Adjusting update rate for partition information

By default, the profile will scan for partitions the first time it is ever used by Snakemake and will store data about available partitions in a file `partitions.yaml`. It will then check again and update the information every *N* days (30 days by default). Note that the information is updated only when the profile is used by Snakemake. You can change the partitions data file name as well as the update rate in the `scheduler` field of the file `slurm.yaml`.
