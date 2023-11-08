# Whole-slide image segmentation of Cell DIVE multiplex microscopy images

This work aims to facilitate and simplify the initial step of image segmentation for whole-slide image analysis of multiplexed images generated using the Cell DIVE imaging platform. This segmentation pipeline uses the well-established `DeepCell` library based on the `Mesmer/TissueNet` model and is adapted from our previously published work (Korsunsky et al, 2022): https://github.com/immunogenomics/FibroblastAtlas2022/tree/main/Analyses_imaging and inspired by the ark analysis pipeline (Angelo, 2023): https://github.com/angelolab/ark-analysis. This segmentation pipeline aims to increase code reproducibility for Cell DIVE image analysis as part of a STAR protocol publication (doi: **to be added**).

## Installation

### Windows
If you are using Windows make sure you have `Windows Subsystem for Linux` [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) and the latest `NVIDIA CUDA` [driver](https://www.nvidia.co.uk/Download/index.aspx) for your GPU (if you have one in your system) installed.

Following [this](https://learn.microsoft.com/en-us/windows/wsl/install) official guide, install `WSL` and create a new `Ubuntu`-based `WSL` environment called `Ubuntu` by opening `PowerShell` and simply running:

```bash
wsl --install -d Ubuntu
```

It will ask you to create a user account and set a password. Make sure that you keep note of these as they are not linked to your Windows login. The next step assumes you have set the user name to be `ubuntu`, so adjust the following command if you chose a different username.

To enter the newly created `WSL` environment `Ubuntu` as the user `ubuntu` you set in the previous step run the following in the `PowerShell`:

```bash
wsl -d Ubuntu -u ubuntu
```

### System preparation and installing Singularity 
#### WSL/Ubuntu or native Ubuntu
The following instructions assume that you are either running Ubuntu 20.04/22.04 LTS on either WSL (see instructions above) or natively and you have access to the console (see previous step for WSL).

If on Windows and you have not yet entered the previously created `WSL` environment, run the following to enter `Ubuntu` `WSL` environment as user `ubuntu`:

```bash
wsl -d Ubuntu -u ubuntu
```

First, we have to install the relevant `NVIDIA` tools to be able to utilise the GPU and `singularity` to deploy and run containers. Make sure you are executing the following commands in order.

We start by setting the version of `SingularityCE` we will be installing and determining the name and version of our Ubuntu distribution:

```bash
SINGULARITY_VER="4.0.0"
UBUNTU_CODENAME=$( lsb_release -cs )
UBUNTU_VERSION=$( lsb_release -rs )
```

Next, we install the `libnvidia-container-tools`. As part of this, we have to add and sign a new repository provided by `NVIDIA`. To do so, we first fetch and add the signing key:

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/libnvidia-container.gpg
```
Then, fetch the repository file
```bash
curl -s -L https://nvidia.github.io/libnvidia-container/ubuntu${UBUNTU_VERSION}/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/libnvidia-container.list
```
and assign the new signing key to repository:
```bash
sudo sed -i 's#deb http#deb [signed\-by=/etc/apt/trusted\.gpg\.d/libnvidia-container\.gpg] http#' /etc/apt/sources.list.d/libnvidia-container.list
```
Now, we update the metadata from the new repositories
```bash
sudo apt update
```
and install libnvidia-container-tools:
```bash
sudo apt install libnvidia-container-tools
```

Next, we download `SingularityCE`,
```bash
mkdir -p ~/Downloads \
&& cd ~/Downloads \
&& wget https://github.com/sylabs/singularity/releases/download/v${SINGULARITY_VER}/singularity-ce_${SINGULARITY_VER}-${UBUNTU_CODENAME}_amd64.deb
```
install it
```bash
sudo apt install ./singularity-ce_${SINGULARITY_VER}-${UBUNTU_CODENAME}_amd64.deb
```
and link the `nvidia-container-cli` tool with `Singularity` by setting the path for nvidia-container-cli in singularity.conf
```bash
sudo sed -i "s#\# nvidia\-container\-cli path =.*#nvidia-container-cli path = $( which nvidia-container-cli )#" /etc/singularity/singularity.conf
```

#### Verify Singularity installation and GPU access
To verify that your `WSL` Ubuntu installation has access to your NVIDIA GPUs run:
```bash
nvidia-smi
```
If setup correctly, this should display information about the system's GPUs on the screen.

To verify that both `nvidia-container-cli` tools and `Singularity` were properly installed, setup and that container have access to the GPUS run:
```bash
singularity run --nv --nvccli docker://nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```
This starts a container with access to all GPUs installed in your systems and prints information about them to the screen. If you can see info about your GPUs being displayed then you have correctly setup up `Singularity`.


### Build whole-slide image segmentation container

We start by creating a `builds` folder in the HOME `~` directory and cloning/downloading this repository from GitHub: 

```bash
mkdir -p ~/builds \
&& cd ~/builds \
&& git clone https://github.com/KIR-CellDIVE/wsi-segmentation.git
```
Next, we build a singularity container called `wsi_segmentation.sif` based on definition file `container.def`:

```bash
cd wsi-segmentation/singularity \
&& sudo singularity build wsi_segmentation.sif Singularity
```

In order to make it easier to run the container in the future we create two bash scripts `wsi-segmentation-gpu` and `wsi-segmentation-cpu` in `~/.local/bin` that can simply be called from anywhere inside the console. Adapt these commands if you decide to download and build the container in a different directory. (Skip this step if you'd rather start the containers directly yourself). 

We make sure that `~/.local/bin` exists.
```bash
mkdir -p ~/.local/bin
```
Then, we create two bash scripts in `~/.local/bin` to make starting the container to run the segmentation more straightforward.

```bash
echo "#! /bin/bash
## run wsi-segmentation with GPU acceleration
[ -d "/mnt" ] && singularity \"\$@\" run --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/singularity/wsi_segmentation.sif || singularity run \"\$@\" --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/singularity/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-gpu
```

```bash
echo "#! /bin/bash
## run wsi-segmentation without GPU acceleration
[ -d "/mnt" ] && singularity run \"\$@\" --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/singularity/wsi_segmentation.sif || singularity run \"\$@\" --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/singularity/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-cpu
```
Lastly, we make these two bash scripts executable

```bash
chmod +x ~/.local/bin/wsi-segmentation-gpu
```
```bash
chmod +x ~/.local/bin/wsi-segmentation-cpu
```
and reload the `~/.profile` file to add `~/.local/bin` to `$PATH`.
```bash
source ~/.profile
```



## Run whole-slide image segmentation

If you have followed the installation step you should be able to run the whole-slide image segmentation Jupyter Notebook server now. If you are on `Windows` and you use `WSL`, first open `PowerShell` and enter the previously created WSL environment `Ubuntu` as the user `ubuntu` if you haven't already done so:

```bash
wsl -d Ubuntu -u ubuntu
```

Once you are in the `WSL` environment you can run faster GPU-accelerated segmentation (if you have a NVIDIA GPU) by typing
```bash
wsi-segmentation-gpu ## for gpu accelerated segmentation
```

or only using the CPU to perform segmentation by typing
```bash
wsi-segmentation-cpu ## for cpu accelerated segmentation
```

> You can pass additional singularity arguments if you want. For example, to bind a results folder to a directory `/data` to make it more easily accessible inside the notebook. In `WSL` the `C:` drive, `D:` drive, etc are mounted and located at `/mnt/c`, `/mnt/d`, etc, respectively. To mount your data folder to `/data` start the notebooks as follows:
>```bash 
> wsi-segmentation-gpu --bind /path/to/result:/data
>```
>

You should now see a link similar to `http://127.0.0.1:9999/lab/workspaces/lab?reset?token=...`, copy it and open it in your preferred browser. Then, in the left sidebar navigate to the `notebooks` folder and open the `1_WSI_Deepcell_Segmentation.ipnyb` notebook. Follow the instructions at the top of the notebook to save and open a copy of the notebook. Once done, you can start the cell segmentation of your Cell DIVE images utilising the `DeepCell` segmentation model and obtain a per-cell marker expression table.

## What to do next after the segmentation 
By the end of the notebook you should have created a file and folder structure, a segmentation mask and per-cell statistic which can be plugged into the `ark-analysis` toolbox ([Documentation](https://ark-analysis.readthedocs.io/en/latest/)/[GitHub](https://github.com/angelolab/ark-analysis)) starting from the [2 - "Pixel clustering with pixie" notebook](https://github.com/angelolab/ark-analysis#2-pixel-clustering-with-pixie). We also provide a `Singularity` container similar to the one found in this repository to run the `ark-analysis` toolbox. Alternatively, you might also want to consider other downstream analysis pipelines such as [Fibroblast Atlas 2022](https://github.com/immunogenomics/FibroblastAtlas2022) or [SpOOx](https://github.com/Taylor-CCB-Group/SpOOx/).

## macOS installation
`Singularity` can also be installed under MacOS making use of virtualisation using `Vagrant`. However, we can not give any guarantees of support for running this container and segmentation notebook under macOS. Thus, please refer to the official [Singularity Documentation](https://docs.sylabs.io/guides/3.0/user-guide/installation.html#mac) for detailed installation instructions of the container environment. These installation instruction should provide you with a Linux environment, which you can use to build the whole-slide image segmentation container by following the steps above. However, at this moment in time this method does not support GPU-accelerated segmentation which will make it very slow for large Cell DIVE images.


## References and Acknowledgments

The work in this repository and protocol paper was based on [Fibroblast Atlas 2022](https://github.com/immunogenomics/FibroblastAtlas2022), inspired by and further adapted from the [ark-analysis] toolbox (https://github.com/angelolab/ark-analysis).


## How to cite

If you use this work as part of your analysis please cite this `wsi-segmentation` repo directly (https://github.com/KIR-CellDIVE/wsi-segmentation) as well as the accompanying publication: (**to be added**). Please also refer to the repositories acknowledged here and ensure compliance with all licensing requirements.

* Authors, Title, Journal, Year, DOI
