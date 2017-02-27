#!/usr/bin/env bash

# Run tests
export PATH="$HOME/miniconda2/bin/:$HOME/EMAN2/bin:$PATH"
export PYTHONPATH="$HOME/EMAN2/lib:$HOME/EMAN2/bin:$PYTHONPATH"
export EMAN2DIR=$HOME/EMAN2

sudo apt-get install patchelf

ldd /home/ubuntu/EMAN2/lib/libpyAligner2.so
ldd /home/ubuntu/EMAN2/lib/libEM2.so
patchelf --print-rpath /home/ubuntu/EMAN2/lib/libpyAligner2.so
patchelf --print-rpath /home/ubuntu/EMAN2/lib/libEM2.so

e2version.py
e2speedtest.py
e2display.py -h
