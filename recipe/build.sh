#!/bin/bash

build_dir="${SRC_DIR}/../build_eman"

rm -rf $build_dir
mkdir -p $build_dir
cd $build_dir

cmake $SRC_DIR

make -j${CPU_COUNT}
make install

cp "${RECIPE_DIR}/setup.py" .
$PYTHON setup.py install --single-version-externally-managed --record record.txt
