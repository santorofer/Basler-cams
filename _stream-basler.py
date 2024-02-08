#!/usr/bin/env python3

import sys
import os

import MDSplus

tree = sys.argv[1]
shot = sys.argv[2]
path = sys.argv[3]

os.environ['DEBUG_DEVICES'] = '4'

t = MDSplus.Tree(tree, int(shot))
device = t.getNode(path)
device.start_stream()

print('all done')

