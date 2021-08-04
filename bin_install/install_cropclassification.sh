#!/bin/bash

# If no parameters passed, show help...
if [ -z "$var" ]
then
  echo
  echo Hello! If you want to override some default options this is possible as such:
  echo 'install_cropclassification.sh --envname cropclassificationdev --envname_backup cropclassificationdev_bck_2020-01-01 --condadir "/home/Miniconda3" --fordev Y'
  echo 
  echo The parameters can be used as such:
  echo     - envname: the name the new environment will be given 
  echo     - envname_backup: if the environment already exist, it will be 
  echo       backupped to this environment
  echo     - condadir: the directory where cona is installed
  echo     - fordev: for development: if Y is passed, only the dependencies 
  echo       for orthoseg will be installed, not the orthoseg package itself
fi

# Extract the parameters passed
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -e|--envname) envname="$2"; shift ;;
        -cd|--condadir) condadir="$2"; shift ;;
        -eb|--envname_backup) envname_backup="$2"; shift ;;
        -od|--fordev) fordev="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Format current date
today=$(date +%F)

# If not provided, init parameters with default values
if [ -z "$envname" ]; then envname="cropclassification" ; fi
if [ -z "$envname_backup" ]; then envname_backup="${envname}_bck_${today}" ; fi
if [ -z "$condadir" ]; then condadir="$HOME/Miniconda3" ; fi
if [ -z "$fordev" ]; then fordev="N" ; fi

# If no parameters are given, ask if it is ok to use defaults
echo
echo "The script will be ran with the following parameters:"
echo "   - envname=$envname"
echo "   - envname_backup=$envname_backup"
echo "   - condadir=$condadir"
echo "   - fordev=$fordev"
echo

read -p "Do you want to move on with these choices? (y/n)" -n 1 -r
echo    
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 # handle exits from shell or function but don't exit interactive shell
fi

# Init conda
conda_init=$condadir/etc/profile.d/conda.sh
if [ -f "$conda_init" ]; then
    . "$conda_init"
else
    echo "STOP: cannot init conda because $conda_init does not exist."
    exit 
fi

#-------------------------------------
# RUN!
#-------------------------------------
echo
echo Backup existing environment
echo -------------------------------------

if [[ ! -z "$envname_backup" ]]
then
  if [[ -d "$condadir/envs/$envname/" ]]
  then
    echo "Do you want to take a backup from $envname?"
    if [[ -d "$condadir/envs/$envname_backup/" ]]
    then
      echo "REMARK: $envname_backup exists already, so will be overwritten by a new backup!"
    fi
    
    read -p "y=take backup, n=don't take backup but proceed, c=stop script (y/n/c)" -n 1 -r
    echo    
    if [[ $REPLY =~ ^[Cc]$ ]]
    then
        [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 # handle exits from shell or function but don't exit interactive shell
    elif [[ $REPLY =~ ^[Yy]$ ]]
    then  
      conda create --name "$envname_backup" --clone "$envname" --offline
    fi
  else 
    echo "No existing environment $envname found to backup"
  fi
fi

echo
echo Create/overwrite environment
echo -------------------------------------
if [[ -d "$condadir/envs/$envname/" ]]
then
  echo "First remove conda environment $envname"
  conda env remove -y --name $envname

  echo "Also really delete the env directory, to evade locked file errors"
  rm -rf $condadir/envs/$envname
fi
echo "Create and install conda environment $envname"
conda create -y --name $envname
conda activate $envname
conda config --env --add channels conda-forge
conda config --env --set channel_priority strict

# List of dependencies + reasons for specific versions.
#
# Remark: the dependencies of tensorflow can be found here: 
# https://libraries.io/pypi/tensorflow
#
# python: 3.8 is the only version that is tested on
# --- General dependencies ---
# rasterio: tested till version 1.2
# --- Tensorflow dependencies available on conda ---
# numpy: for tf: needs 1.19, otherwise replaced with pip version
# h5py: for tf: <3, otherwise impossible to load saved models
conda install -y python=3.6 "h5py<3" fiona geopandas pyarrow psutil rasterio rasterstats scikit-learn keras tensorflow

# For the following packages, no conda package is available or -for tensorflow- no recent version.
if [[ ! $fordev =~ ^[Yy]$ ]]
then
  echo
  echo "Install the pip package"
  echo
  #pip install "tensorflow>=2.5,<2.6" cropclassification
  pip install cropclassification
else
  echo
  echo "Prepare for development: conda install dev tools"
  echo
  conda install -y pylint pytest rope
 
  echo
  echo "Prepare for development: pip install dependencies of orthoseg that need pip"
  echo
  #pip install "tensorflow>=2.5,<2.6" 
fi

# Export the environment to a .yml file
mkdir -p yml
conda env export > "./yml/$envname_${today}.yml"

# Deactivate new env
conda deactivate

# Clean the cache dir + deactivate base env
#conda clean --all
conda deactivates

# Pause
read -s -n 1 -p "Press any key to continue..."
