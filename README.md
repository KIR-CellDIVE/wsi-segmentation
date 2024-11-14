# Whole-slide image segmentation of Cell DIVE multiplex microscopy images

This work aims to facilitate and simplify whole-slide segmentation as the first step of image analysis for researchers using the Cell DIVE multiplex imaging platform. This segmentation pipeline uses the well-established `DeepCell` library and `Mesmer` model. The notebook structure is inspired by the ark analysis pipeline (Angelo, 2023): https://github.com/angelolab/ark-analysis. This segmentation pipeline is also part of a STAR protocol publication (doi: TO BE ADDED).

## Installation

### Windows
If you are using Windows make sure you have `Windows Subsystem for Linux` [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) and the latest `NVIDIA CUDA` [driver](https://www.nvidia.co.uk/Download/index.aspx) for your GPU (if you have one in your system) installed.

Following [this](https://learn.microsoft.com/en-us/windows/wsl/install) official guide, install `WSL` and create a new `Ubuntu`-based `WSL` environment called `Ubuntu` by opening `PowerShell` and simply running:

```bash
wsl --install -d Ubuntu-22.04
```

It will ask you to create a user account and set a password. Make sure that you keep note of these as they are not linked to your Windows login. The next step assumes you have set the user name to be `ubuntu`, so adjust the following command if you chose a different username.

Now, let's rename the WSL container to something more specific and so we make sure that this WSL container is used only for this specific purpose:

```bash
wsl --shutdown
wsl --export Ubuntu-22.04 ubuntu-2204.tar
wsl --import Ubuntu_DIVEMAP .\Ubuntu_DIVEMAP ubuntu-2204.tar
```

Lastly, we want to make the `ubuntu` user the default user. This is so you do not log in as the `root` user by default. We achieve as follows:

```bash
wsl -d Ubuntu_DIVEMAP -u root -e sh -c @"
echo "[user]
default=ubuntu" >> /etc/wsl.conf
"@
```

(Optional) You can now delete the original `Ubuntu-22.04` WSL container by typing:
```bash
wsl --unregister Ubuntu-22.04
rm ubuntu-2204.tar
```

To enter the newly created `WSL` environment `Ubuntu` as the user `ubuntu` you set in the previous step run the following in the `PowerShell`:

```bash
wsl -d Ubuntu_DIVEMAP -u ubuntu
```

Finally, to make the non-privileged `ubuntu` user the default user run the following command all at once in the `PowerShell`:  
```bash
wsl -d Ubuntu_DIVEMAP -u root -e sh -c @"
cat >> /etc/wsl.conf<< EOF
[user]
default=ubuntu
EOF
"@
```

### System preparation and installing Apptainer 
#### WSL/Ubuntu or native Ubuntu
The following instructions assume that you are either running Ubuntu 20.04/22.04 LTS on either WSL (see instructions above) or natively and you have access to the console (see previous step for WSL).

If on Windows and you have not yet entered the previously created `WSL` environment, run the following to enter `Ubuntu` `WSL` environment as user `ubuntu`:

```bash
wsl -d Ubuntu -u ubuntu
```

First, we have to install the relevant `NVIDIA` tools to be able to utilise the GPU and `Apptainer` to deploy and run containers. Make sure you are executing the following commands in order.

First, we install the `nvidia-container-toolkit`. As part of this, we have to add and sign a new repository provided by `NVIDIA`. To do so, we first fetch and add the signing key:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```
Then, fetch the repository file and assign the new signing key to repository
```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

Now, we update the metadata from the new repositories
```bash
sudo apt update
```
and install nvidia-container-toolkit:
```bash
sudo apt-get install -y nvidia-container-toolkit
```

Next, we are going to install `Apptainer`. To do so we first install the *software-properties-common* package in order to be able to add PPA (Personal Package Archive) to the repositories:

```bash
sudo apt update
sudo apt install -y software-properties-common
```
Then, we add the Apptainer PPA:
```bash
sudo add-apt-repository -y ppa:apptainer/ppa
sudo apt update
```

Finally, we install `Apptainer`:
```bash
sudo apt install -y apptainer
```

#### Verify Apptainer installation and GPU access
To verify that your `WSL` Ubuntu installation has access to your NVIDIA GPUs run:
```bash
nvidia-smi
```
If setup correctly, this should display information about the system's GPUs on the screen.

To verify that both `nvidia-container-cli` tools and `Apptainer` were properly installed, setup and that container have access to the GPUS run:
```bash
apptainer run --nv --nvccli docker://nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```
This starts a container with access to all GPUs installed in your systems and prints information about them to the screen. If you can see info about your GPUs being displayed then you have correctly setup up `Apptainer`.


### Build whole-slide image segmentation container

If you on Windows enter your previously created WSL virtual environment by typing `wsl -d Ubuntu -u ubuntu` (if you have not already done so) or if you on Linux open your favourite terminal emulator. To build the WSI segmentation container we start by creating a `builds` folder in the HOME `~` directory and cloning/downloading this repository from GitHub: 


```bash
mkdir -p ~/builds \
&& cd ~/builds \
&& git clone https://github.com/KIR-CellDIVE/wsi-segmentation.git
```
Next, we build a Apptainer container called `wsi_segmentation.sif` based on definition file `Apptainer`:

```bash
cd wsi-segmentation/apptainer \
&& sudo apptainer build wsi_segmentation.sif Apptainer
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
[ -d "/mnt" ] && apptainer \"\$@\" run --writable-tmpfs --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/apptainer/wsi_segmentation.sif || apptainer run --writable-tmpfs \"\$@\" --bind /:/opt/analysis/host --nv --nvccli $HOME/builds/wsi-segmentation/apptainer/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-gpu
```

```bash
echo "#! /bin/bash
## run wsi-segmentation without GPU acceleration
[ -d "/mnt" ] && apptainer run --writable-tmpfs \"\$@\" --bind /mnt:/opt/analysis/drives --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/apptainer/wsi_segmentation.sif || apptainer run --writable-tmpfs \"\$@\" --bind /:/opt/analysis/host $HOME/builds/wsi-segmentation/apptainer/wsi_segmentation.sif" > ~/.local/bin/wsi-segmentation-cpu
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

> You can pass additional Apptainer arguments if you want. For example, to bind a results folder to a directory `/data` to make it more easily accessible inside the notebook. In `WSL` the `C:` drive, `D:` drive, etc are mounted and located at `/mnt/c`, `/mnt/d`, etc, respectively. To mount your data folder to `/data` start the notebooks as follows:
>```bash 
> wsi-segmentation-gpu --bind /path/to/result:/data
>```
>

You should now see a link similar to `http://127.0.0.1:9999/lab/workspaces/lab?reset?token=...`, copy it and open it in your preferred browser. Then, in the left sidebar navigate to the `notebooks` folder and open the `1_WSI_Deepcell_Segmentation.ipnyb` notebook. Follow the instructions at the top of the notebook to save and open a copy of the notebook. Once done, you can start the cell segmentation of your Cell DIVE images utilising the `DeepCell` segmentation model and obtain a per-cell marker expression table.

## What to do next after the segmentation 
By the end of the notebook you should have created file and folder structure, a segmentation mask and per-cell statistic which can be plugged into the `ark-analysis` toolbox ([Documentation](https://ark-analysis.readthedocs.io/en/latest/)/[GitHub](https://github.com/angelolab/ark-analysis)) starting from the [2 - "Pixel clustering with pixie" notebook](https://github.com/angelolab/ark-analysis#2-pixel-clustering-with-pixie). We also provide `Apptainer` container similar to the one found in this repository to run the `ark-analysis` toolbox [link](). Alternatively, you might also want to consider other whole-slide multiplex image analysis approaches such as the single cell inspired workflow established in [Fibroblast Atlas 2022](https://github.com/immunogenomics/FibroblastAtlas2022) which is part of `DIVEMAP` pipeline and can be found [here](https://github.com/KIR-CellDIVE/wsi-analysis) or an end-to-end pipeline such as [SpOOx](https://github.com/Taylor-CCB-Group/SpOOx/).

## macOS installation
`Apptainer` can also be installed under MacOS making use of virtualisation using `Vagrant`. However, we can not give any guarantees and support for running this container and segmentation notebook under macOS. Thus, please refer to the official [Apptainer Documentation](https://apptainer.org/docs/admin/main/installation.html#mac) for detailed installation instructions of the container environment. These installation instruction should provide you with a Linux environment, which you can use to build the whole-slide image segmentation container. However, at this moment in time this method does not support GPU-accelerated segmentation which will make it very slow for large Cell DIVE slides.


## References and Acknowledgments

The work in this repository and protocol paper was based on [Fibroblast Atlas 2022](https://github.com/immunogenomics/FibroblastAtlas2022), inspired by and further adapted from the [ark-analysis] toolbox (https://github.com/angelolab/ark-analysis).


## How to cite

If you use this work as part of your analysis please cite this `wsi-segmentation` repo directly (https://github.com/KIR-CellDIVE/wsi-segmentation) as well as the accompanying publication: (**to be added**). Please also refer to the repositories acknowledged here and ensure compliance with all licensing requirements.

* Authors, Title, Journal, Year, DOI
