#!/usr/bin/env python

import os

e2real="{}/sx_real.py".format(os.path.dirname(os.path.abspath(__file__)))
os.execlp("ipython","ipython","-i",e2real)