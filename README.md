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

Both modules are available in Conda and PyPi; if you're using a Conda environment for Snakemake, you shouldn't have to install anything. If not, they can be installed with pip in a user environment (*e.g.* on a cluster) with:

```bash
pip install --user pyyaml
pip install --user snakemake
```

#### Installing the profile

```bash
git clone https://github.com/RomainFeron/snakemake-slurm.git
cd snakemake-slurm
./INSTALL
```

By default, the profile will be installed to `~/.config/snakemake/slurm`. You can specify a different name for the profile: 

```bash
git clone https://github.com/RomainFeron/snakemake-slurm.git
cd snakemake-slurm
./INSTALL <profile_name>
```

In this case, the profile will be installed in `~/.config/snakemake/<profile_name>`.


#### Updating the profile

To update the profile's code while retaining configuration file, pull from the `snakemake-slurm` and run the `UPDATE` script:
```bash
# From within the snakemake-slurm directory (not the directory where the profile was installed)
git pull
./UPDATE
```

If you used a name other than the default `slurm` for the profile, specify the name when running `UPDATE`:
```bash
# From within the snakemake-slurm directory (not the directory where the profile was installed)
git pull
./UPDATE <profile_name>
```

Updating the profile will update the profile's code but not the configuration (yaml) files, so that your configuration is saved. To update all files (including configuration files) and reset the partitions info file, use the following command:
```bash
# From within the snakemake-slurm directory (not the directory where the profile was installed)
git pull
./FULL_UPDATE (<profile_name>)
```

#### Special notes for UNIL HPC users (Curnagl)

Since this profile is mainly used by users of the UNIL HPC Curnagl, I thought I'd share my configuration for this platform. Since we don't need to split jobs between Axiom and Wally anymore, setup is a lot easier; the only important thing for most users is to blacklist two partitions:

```yaml
# Partitions to remove from submit list
blacklist:
  - interactive
  - gpu
```

If you use a GPU for some steps in your workflows, don't blacklist `gpu`.

**Note**: I recommend to install Conda on `/work` and create an environment dedicated only to Snakemake with Conda. By default Conda is installed in your home (`/users/<username>`) which has pretty low storage and file number quotas.

## Usage

### Using the profile

To run Snakemake with this profile, use the runtime parameter `--profile`: `snakemake --profile slurm` (replace `slurm` with `<profile_name>` if you installed the profile under a different name). For more information on Snakemake profiles, check the [official Snakemake documentation](https://snakemake.readthedocs.io/en/stable/executing/cli.html?#profiles).

### Specifying parameter values

#### Default slurm parameters

The profile will check Snakemake's jobscript for all parameters defined in the `options` field of the file `slurm.yaml` in `~/.config/snakemake/<profile_name>`. By default, these parameters are:

| Option | Description | Snakemake keyword |
|---|---|---|
| threads | Number of CPUs to request at submission | `threads` |
| memory | Maximum memory to request at submission (**in Mb**) | **`resources: mem_mb`**<br>`resources: memory`<br>`params: mem_mb`<br>`params: memory`|
| runtime | Maximum runtime to request at submission<br>(**format: M, M:S, H:M:S, D-H, D-H:M, or D-H:M:S**, see [SLURM doc](https://slurm.schedmd.com/sbatch.html#OPT_time) | `params: runtime`|
| runtime_s | Maximum runtime to request at submission (**in seconds**) | **`resources: runtime_s`**<br>`params: runtime_s`|
| log | Path to log file | `log` |
| partition | Partition to submit the job to | `params: partition`|

For instance a rule requiring 8 threads, 4 days runtime, and 16 Gb of memory will look like:

```python
rule example:
    output: 'example.txt'
    threads: 8
    resources:
        mem_mb = 16000,
        runtime_s = 345600  # 4 days = 345600 seconds
    shell:
    'echo "example" > {output}'
```

Another example specifying runtime in format D-HH:MM:SS and using the `long` partition:

```python
rule example:
    output: 'example.txt'
    threads: 8
    resources:
        mem_mb = 16000
    params:
        runtime = '4-00:00:00',
        partition = 'long'
    shell:
    'echo "example" > {output}'
```

**Note :** it is advised to specify runtime and memory with the `resources` keyword using `mem_mb` and `runtime_s`, as it allows Snakemake to resubmit the job with higher memory requirements in case of failure.

#### Implementing custom slurm parameters

You can implement additional parameters by adding an entry to the `options` field of the file `slurm.yaml`, with format:

```yaml
options:
    <option_name>: <slurm flag>={}
```

In this case, `<option_name>` should match the name of the Snakemake rule option, and `<slurm_flag>` is the flag used to specify this option with the `sbatch` command. The `{}` will be substituted for the option's value if the value was specified in the Snakemake rule.

Below is an example implementing the `--mail-type` slurm flag using a parameter `mail` in Snakemake:

**slurm.yaml:**

```yaml
options:
    mail: --mail-type={}
```

**Snakefile:**

```python
rule example:
    output: 'example.txt'
    params:
        mail: 'END'
    shell:
    'echo "example" > {output}'
```

In the Snakemake rule, option values can be specified
- at the rule level (*e.g.* `threads`)
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

By default, the profile will scan for partitions the first time it is ever used by Snakemake and will store data about available partitions in a file `partitions.yaml`. It will then check again and update the information every *N* days (1 day by default). Note that the information is updated only when the profile is used by Snakemake. You can change the partitions data file name as well as the update rate in the `scheduler` field of the file `slurm.yaml`.

## Troubleshooting

### Job gets stuck in PD state

You can get information on why the job is stuck from the 'REASON' field in the output of `squeue -u <username>`.

In some cases, partition permissions are not configured properly and snakemake-slurm will try to submit jobs to a partition that is not available for you. There is no official reason code for this, but it may contain the word 'Permission' somewhere. In this case, check which partition the job was submitted to with `scontrol show job <job_id>` and add this partition to the [blacklist](#blacklisting-partitions).
