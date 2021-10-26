#!/bin/bash -f
 
echo 
echo In case of any problem, please contact: tomas.odstrcil@gmail.com or giovanni.tardini@ipp.mpg.de for local issues

source /etc/profile.d/modules.sh

module purge 
module load mkl intel ffmpeg anaconda/3/2019.03 aug_sfutils

export LD_LIBRARY_PATH=${MKL_HOME}/lib/intel64_lin:/afs/ipp-garching.mpg.de/home/t/todstrci/SuiteSparse/lib/
export C_INCLUDE_PATH=${LD_LIBRARY_PATH}:/afs/ipp-garching.mpg.de/home/t/todstrci/SuiteSparse/lib/

#load mencoder, used only in nogui.py

export PATH=${PATH}:/afs/@cell/common/soft/visualization/mencoder/svn-2012-11-15/amd64_sles11/bin


export LD_LIBRARY_PATH=${MKL_HOME}/lib/intel64_lin:/afs/ipp-garching.mpg.de/home/t/todstrci/SuiteSparse/lib/
export PYTOMO=/afs/ipp/home/g/git/python/tomo_dev
rootdir=`dirname $0`                       # may be relative path
export PYSPECVIEW=`cd $rootdir && pwd`  # ensure absolute path


python $PYSPECVIEW/pyspecview.py  $@
