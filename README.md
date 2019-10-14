# Snakemake profile for Slurm schedulers

This profile is heavily inspired from the Slurm profile in Snakemake's official profiles [repository](https://github.com/Snakemake-Profiles/slurm). This profile is great, but it is missing some features and documentation. The present Snakemake profile was developed to address these points and implements the following features:
- No cookiecutter dependency
- Comprehensive documentation making the profile easy to use
- "Smart" handling of partitions
- Customability through YAML files
- "Clean" implementation to allow adding new features efficiently

**This is a work in progress. Feature requests, issues, and pull requests welcome !**

## Installation

#### Requirements

To function properly, this profile requires the following python modules:

- `pyyaml`
- `snakemake`

Both modules are available in PyPi and can be installed with pip. To install these modules in a user environment (*e.g.* on a cluster), run:

```bash
pip install --user pyyaml
pip install --user snakemake
```

#### Installing the profile

```bash
git clone https://github.com/RomainFeron/snakemake-slurm.git
./INSTALL
```

By default, the profile will be installed to `~/.config/snakemake/slurm`. You can specify a different name for the profile by running `./INSTALL <profile_name>`; then, the profile will be installed in `~/.config/snakemake/<profile_name>`.


#### Updating the profile

```bash
git clone https://github.com/RomainFeron/snakemake-slurm.git
./UPDATE
```

Updating the profile will update the profile's code but not the configuration (yaml) files, so that your configuration is saved. If you installed the profile in a specific directory `<profile_name>`, run the command `./UPDATE <profile_name>` instead.


#### Special notes for UNIL HPC users (wally / axiom)

Since this profile is mainly used by users of the UNIL HPC wally/axiom, I thought I'd share my configuration for this platform. I setup two separate profiles for wally and axiom with the following commands:

```bash
./INSTALL wally
./INSTALL axiom
```

I then edited the file `slurm.yaml` for each profile to blacklist partitions from the other cluster:

- **Wally**:

```yaml
blacklist:
    - ax-normal
    - ax-long
```

- **Axiom**:

```yaml
blacklist:
    - normal
    - long
```

This way, I can run Snakemake on axiom (if the data is on /scratch/axiom) with `--profile axiom`, and on wally (if the data is on /scratch/wally) with `--profile wally`.

**Note**: you should install Miniconda in your home, which can be accessed from both axiom and wally nodes. It could cause storage problems if you're using a lot of tools but there is no other solution at the moment, except duplicating your Miniconda install on both /scratch/axiom and /scratch/wally.

## Usage

### Using the profile

To run Snakemake with this profile, use the runtime parameter `--profile slurm` (replace `slurm` with `<profile_name>` if you installed the profile under a different name): `snakemake --profile slurm`. For more information on Snakemake profiles, check the [official Snakemake documentation](https://snakemake.readthedocs.io/en/latest/executable.html#profiles).

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
    'echo "example" > {output}'
```

**Note :** it is advised to specify memory with the `resources` keyword, as it allows Snakemake to resubmit the job with higher memory requirements in case of failure.

You can implement additional parameters by adding an entry to the `options` field of the file `slurm.yaml`, with format:
```yaml
options:
    <option_name>: <slurm flag>={}
```
In this case, `<option_name>` should match the name of the Snakemake rule option, and `<slurm_flag>` is the flag used to specify this option with the `sbatch` command. The `{}` will be substituted for the option's value if the value was specified in the Snakemake rule.

In the Snakemake rule, option values can be specified 
- at the rule level (*e.g.* threads)
- within the `params` keyword
- within the `resources` keyword. 

The profile will first look for the option in `resources`, then `params`, then at the rule level.

### Blacklisting partitions

The profile automatically detects all partitions available on the cluster and selects the one with highest priority that satisfies the resources requirements. If you do not want Snakemake to submit to specific partitions at all, you can specify these partitions in the `blacklist` field of the file `slurm.yaml`.

**Example**:
```yaml
blacklist:
    - long
```

### Adjusting update rate for partition information

By default, the profile will scan for partitions the first time it is ever used by Snakemake and will store data about available partitions in a file `partitions.yaml`. It will then check again and update the information every *N* days (30 days by default). Note that the information is updated only when the profile is used by Snakemake. You can change the partitions data file name as well as the update rate in the `scheduler` field of the file `slurm.yaml`.
