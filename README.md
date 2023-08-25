# Whole slide image segmentation of CellDIVE multiplex microscopy images

This work aims to facilitate and simplify the intial step of image analysis that is whole slide image segmentation for reseachers using the CellDIVE multiplex imaging platform. This segmentation pipeline uses well-established `DeepCell` `Mesmer` model. This segmentation pipeline is also part of a STAR protocol publication (doi:?????).

## Installation

### Windows specific steps
If you are using Windows make sure you have `WSL` ([link](https://learn.microsoft.com/en-us/windows/wsl/install)) and the latest `NVIDIA CUDA` driver ([link](https://www.nvidia.co.uk/Download/index.aspx)) for your GPU (if you have one in your system) installed.

Following this official [guide](https://learn.microsoft.com/en-us/windows/wsl/install), install `WSL` and create a new `Ubuntu`-based `WSL` evironment called `Ubuntu` by opening `PowerShell` and simply running:

```bash
wsl --install -d Ubuntu
```

It will ask you to create a user account and set a password. Make sure that you keep note of these as they are not linked to you Windows login. The next steps assumes you have set the user name to be `ubuntu`, so adjust the following command if you chose a different username.

To enter the newly created WSL enviroment `Ubuntu` as the user `ubuntu` you set in the previous step run the following in the `PowerShell`:

```bash
wsl -d Ubuntu -u ubuntu
```


### WSL/Ubuntu or native Ubuntu - System preparation
The following instructions assume that you are either running Ubuntu 20.04/22.04 LTS on either WSL (see instructions above) or natively and you have access to the console (see previous step for WSL).

First, we have to install the relevant `NVIDIA` tools to be able to utilise the GPU and `singularity` to deploy and run containers. Make sure you are executing the following commands in order.

We start by setting the version of `SingularityCE` we will be installing and determining the name and version of our Ubuntu distribution:

```bash
SINGULARITY_VER="3.11.4"
UBUNTU_CODENAME=$( lsb_release -cs )
UBUNTU_VERSION=$( lsb_release -rs )
```

Next, we install the `libnvidia-container-tools`. As part of this, we have to add and sign a new repository provided by `NVIDIA`.

```bash
## Fetch and add the signing key
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/libnvidia-container.gpg
```
```bash
## Fetch the repository file
curl -s -L https://nvidia.github.io/libnvidia-container/ubuntu${UBUNTU_VERSION}/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/libnvidia-container.list
```
```bash
## Assign new signing key to repository
sudo sed -i 's#deb http#deb [signed\-by=/etc/apt/trusted\.gpg\.d/libnvidia-container\.gpg] http#' /etc/apt/sources.list.d/libnvidia-container.list
```
```bash
## Get the metadata from the new repositories
sudo apt update
```
```bash
## Install libnvidia-container-tools
sudo apt install libnvidia-container-tools
#######################################
```

Next, we download,
```bash
mkdir -p ~/Downloads \
&& cd ~/Downloads \
&& wget https://github.com/sylabs/singularity/releases/download/v${SINGULARITY_VER}/singularity-ce_${SINGULARITY_VER}-${UBUNTU_CODENAME}_amd64.deb
```
install `SingularityCE`
```bash
sudo apt install ./singularity-ce_${SINGULARITY_VER}-${UBUNTU_CODENAME}_amd64.deb
```
and link the `nvidia-container-cli` tool into it.
```bash
# Set path for nvidia-container-cli in singularity.conf
sudo sed -i "s#\# nvidia\-container\-cli path =.*#nvidia-container-cli path = $( which nvidia-container-cli )#" /etc/singularity/singularity.conf
###########################
```

### Build whole slide image segmentation container

We start by creating a `builds` folder in the HOME `~` directory and cloning/downloading this repository into it: 

```bash
### download repository from github ###
mkdir -p ~/builds \
&& cd ~/builds \
&& git clone https://github.com/KIR-CellDIVE/wsi-segmentation.git
#######################################
```
Next, we build a singularity container called `wsi_segmentation.sif` based on definition file `container.def`:

```bash
### build singularity container ###
cd wsi-segmentation \
&& sudo singularity build wsi_segmentation.sif container.def
###################################
```

In order to make it easier to run the container in the future we create to bash scripts `wsi-segmentation-gpu` and `wsi-segmentation-cpu` in `~/.local/bin` that can be simpled called from anywhere inside the console. Adapt these command if you decided to download and build the container in a different directory. (Skip this step if rather start the containers directly yourself). 

We make sure that `~/.local/bin` exists.
```bash
### make sure ~/.local/bin directory exists ###
mkdir -p ~/.local/bin
```
Then, we create two bash scripts in `~/.local/bin` to make starting the container to run the segmentation more straightforward.

```bash
echo "#! /bin/bash
## run wsi-segmentation with GPU acceleration
[ -d "/mnt" ] && singularity \"\$@\" run --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/wsi_segmentation.sif || singularity run \"\$@\" --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-gpu
```

```bash
echo "#! /bin/bash
## run wsi-segmentation without GPU acceleration
[ -d "/mnt" ] && singularity run \"\$@\" --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/wsi_segmentation.sif || singularity run \"\$@\" --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-cpu
```
Lastly, we make these two bash scripts executable

```bash
### make bash scripts executable ###
chmod +x ~/.local/bin/wsi-segmentation-gpu
chmod +x ~/.local/bin/wsi-segmentation-cpu
###############################################
```
and reload the `~/.profile` file.
```bash
### reload ~/.profile to add ~/.local/bin to $PATH ###
source ~/.profile
```



## Run whole slide image segmentation

If you have followed the installation step you should be able to run the whole slide image segmentation jupyter notebook server by simply typing either
```bash
wsi-segmentation-gpu ## for gpu accelerated segmentation
```
or
```bash
wsi-segmentation-cpu ## for cpu accelerated segmentation
```

> **NOTE:** You can pass additional singularity arguments if you want. For example to bind a results folder to a directoty `/data` to make it more easily accessible inside the notebook. In `WSL` the `C:` drive, `D:` drive, etc are mounted and located at `/mnt/c`, `/mnt/d`, etc, respectively. To mount your data folder to `/data` start the notebooks as follows:
>```bash 
> wsi-segmentation-gpu --bind /path/to/result:/data
>```
>

You should now see a link similiar to `http://127.0.0.1:9999/lab?token=...`, copy it and open it in your preferred browser. Then open the `01_wsi_segmentation.ipnyb` notebook and follow the instructions to perform cell segmentation of your CellDIVE slides utilising the `deepcell` segmentation model and obtain a per-cell marker expression table.

## What to do next after the segmentation 
By the end of the notebook you should have created file and folder structure, a segmentation mask and per-cell statistic which can be plugged into the `ark-analysis` toolbox ([Documentation](https://ark-analysis.readthedocs.io/en/latest/)/[GitHub](https://github.com/angelolab/ark-analysis)) starting from the [second notebook](https://github.com/angelolab/ark-analysis#2-pixel-clustering-with-pixie). Alternatively, you might also want to consider other whole slide image multiplex analysis pipelines such as [link](https://github.com/immunogenomics/FibroblastAtlas2022).

## References and Acknowledgments

The work in this repository was partly inspired by and the whole slide segmentation notebook loosely adapted in it's structure from the `ark-analysis` toolbox (https://github.com/angelolab/ark-analysis).


## How to cite

If you use this work was part of your analysis please cite this `wsi-segmentation` repo directly (https://github.com/KIR-CellDIVE/wsi-segmentation) as well as the accompanying publication:

* Authors, Title, Journal, Year, DOI