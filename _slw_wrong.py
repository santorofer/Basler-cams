#!/usr/bin/env python3
import os
import MDSplus
from numpy import array
import math
import time

# some constants needed to make the frames
WIDTH = 640
HEIGHT = 480
SEG_SIZ=1

NUM_FRAMES = 3000
PI = 3.14159
delta_t = 1/30.
trigger_time = 0.0
PATH = "sdn-1::/trees/test"
PATH = "sdn-1::"
#PATH = "."

os.environ['default_tree_path'] = PATH

# create a new tree called test, shot 1
# and add a node to hold the segmented data
tree = MDSplus.Tree("test",1,"NEW")
node = tree.addNode("SEGMENTED").addTag("SEGMENTED")
#node.deleteData() 
tree.write()

total_time = 0.0

# Open the tree and get the node to put the data in.
t = MDSplus.Tree('test', 1)
node = t.SEGMENTED

# make a buffer to hold the computed frames
# make a dummy buffer the size and shape of
# an ENTIRE SEGMENT
#
currFrame = array([0]*(WIDTH*HEIGHT))
currSeg = array([0]*(WIDTH*HEIGHT*SEG_SIZ))
currSeg = MDSplus.Int16Array(currSeg)
currSeg.resize(SEG_SIZ, HEIGHT, WIDTH)

# for each frame
for frameIdx in range(0, NUM_FRAMES):

    m = math.tan((2*PI*frameIdx)/NUM_FRAMES)
    for i in range(WIDTH):
        j = int(round((i-WIDTH/2)*m))

        if j >= -HEIGHT/2 and j < HEIGHT/2:
            currFrame[int((j+HEIGHT/2)*WIDTH+i)] = 255

# reshape the data and call putSegment

    segment = MDSplus.Int16Array(currFrame)
    segment.resize([1,HEIGHT,WIDTH])
    currSeg[frameIdx%SEG_SIZ] = segment
    if frameIdx % SEG_SIZ == (SEG_SIZ-1):
        currTime = float(trigger_time+(frameIdx-SEG_SIZ+1)*delta_t)
        startTime = MDSplus.Float32(currTime)
        endTime = MDSplus.Float32(currTime+(SEG_SIZ-1)*delta_t)
        delta = MDSplus.Float32(delta_t)
        dim = MDSplus.Range(startTime, endTime, delta)
        start_time = time.time()
        node.makeSegment(startTime, endTime, dim, currSeg, -1)
        total_time += time.time() - start_time


print(f"for {NUM_FRAMES} frames to write to {PATH} with segment_length {SEG_SIZ} the total time: {total_time}") 