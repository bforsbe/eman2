#!/usr/bin/env bash

# PLEASE NOTE: This script has been automatically generated by conda-smithy. Any changes here
# will be lost next time ``conda smithy rerender`` is run. If you would like to make permanent
# changes to this script, consider a proposal to conda-smithy so that other feedstocks can also
# benefit from the improvement.

FEEDSTOCK_ROOT=$(cd "$(dirname "$0")/.."; pwd;)

docker info

config=$(cat <<CONDARC

channels:
 - jmbell
 - conda-forge
 - defaults

show_channel_urls: true

CONDARC
)

cat << EOF | docker run -i \
                        -v "${FEEDSTOCK_ROOT}":/feedstock_root \
                        -a stdin -a stdout -a stderr \
                        condaforge/linux-anvil \
                        bash || exit $?

export PYTHONUNBUFFERED=1

echo "$config" > ~/.condarc
# A lock sometimes occurs with incomplete builds. The lock file is stored in build_artefacts.
conda clean --lock

conda install --yes --quiet conda-forge-build-setup
source run_conda_forge_build_setup


# Install the yum requirements defined canonically in the
# "recipe/yum_requirements.txt" file. After updating that file,
# run "conda smithy rerender" and this line be updated
# automatically.
yum install -y libXi-devel libXmu-devel mesa-libGLU-devel


# Embarking on 1 case(s).
    set -x
    export CONDA_PY=27
    set +x
    conda build /feedstock_root/recipe --quiet || exit 1
EOF