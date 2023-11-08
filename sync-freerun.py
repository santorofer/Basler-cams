import pypylon.pylon as pylon
import numpy as np
from PIL import Image
import time
import os
import matplotlib.pyplot as plt

NUM_CAMERAS = 2
FPS = 100  # Hz
TIME_TO_RECORD = 2  # seconds
IMAGES_TO_GRAB = FPS * TIME_TO_RECORD
HEIGHT = 616
WIDTH = 400
DELAY = 5 # seconds

tlf = pylon.TlFactory.GetInstance()
devices = tlf.EnumerateDevices()

cam_array = pylon.InstantCameraArray(NUM_CAMERAS)


for idx, cam in enumerate(cam_array):
    cam.Attach(tlf.CreateDevice(devices[idx]))

cam_array.Open()


cam_array[0].GevTimestampControlLatch()
currentTimestamp = cam_array[0].GevTimestampValue()
print(f'Current Timestamp is {currentTimestamp} for cam0')
actionTime = currentTimestamp + int(DELAY * 1e9)

# store a unique number for each camera to identify the incoming images
for idx, cam in enumerate(cam_array):
    camera_serial = cam.DeviceInfo.GetSerialNumber()
    
    cam.GevIEEE1588 = True
    print(f'PTP enable for {camera_serial}: {cam.GevIEEE1588()}')
    cam.Height = HEIGHT
    cam.Width = WIDTH

    print(f'FPS for {camera_serial}: {cam.SyncFreeRunTimerTriggerRateAbs()}')
    
    # Used to determine which camera the frame is from    
    cam.SetCameraContext(idx)
    
    cam.AcquisitionMode = 'Continuous'

    cam.SyncFreeRunTimerTriggerRateAbs = FPS

    # (SLW) What the fuuuuuu
    cam.SyncFreeRunTimerStartTimeLow = (actionTime & 0x00000000FFFFFFFF)
    cam.SyncFreeRunTimerStartTimeHigh = (actionTime & 0xFFFFFFFF00000000) >> 32
    
    cam.SyncFreeRunTimerUpdate()
    cam.SyncFreeRunTimerEnable = True

    print("actionTime", actionTime)
    print("SyncFreeRunTimerStartTimeLow", cam.SyncFreeRunTimerStartTimeLow())
    print("SyncFreeRunTimerStartTimeHigh", cam.SyncFreeRunTimerStartTimeHigh())

cam_array.StartGrabbing()

from datetime import datetime, timedelta

start_time = datetime.now() + timedelta(seconds=DELAY)

frame_counts = [0]*NUM_CAMERAS
frames_by_camera = [[]]*NUM_CAMERAS

time_list_0 = []
time_list_1 = []

while True:    
    try:
        with cam_array.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException) as res:

            if res.GrabSucceeded():
                img_nr = res.ImageNumber
                cam_id = res.GetCameraContext()
                frame_counts[cam_id] = img_nr
                #print(f"cam #{cam_id}  image #{img_nr}")
                
                frames_by_camera[cam_id].append(res.Array.copy())
                
                time_stamp = res.TimeStamp
                if cam_id == 0:
                    time_list_0.append(time_stamp/1e9)
                else:
                    time_list_1.append(time_stamp/1e9)
                
                # check if all cameras have reached x images
                if min(frame_counts) >= IMAGES_TO_GRAB:
                    print( f"all cameras have acquired {IMAGES_TO_GRAB} frames")
                    break
    except:
        cam_array[0].GevTimestampControlLatch()
        currentTimestamp = cam_array[0].GevTimestampValue()
        print(f'Current Timestamp is {currentTimestamp} for cam0. {actionTime - currentTimestamp}')

cam_array.StopGrabbing()
cam_array.Close()


stop_time = datetime.now()
print('Done streaming, took', stop_time - start_time)

start_time = datetime.now()

for cam_id, frames in enumerate(frames_by_camera):
    for img_nr, frame in enumerate(frames):
        # image = res.Array
        img = Image.fromarray(frame)
        img.save(f'image{cam_id}_{img_nr}.png')


stop_time = datetime.now()
print('Done writing, took', stop_time - start_time)

print('Time stamps comparasion')

figure, axis = plt.subplots(2, 2) 

axis[0,0].plot(time_list_0, 'o', color='r', label='cam 0')
axis[0,0].plot(time_list_1, 'x', color='b', label='cam 1')
axis[0,0].set(ylabel='Unix Timestamps per frame [sec]')

diff = np.subtract(time_list_1, time_list_0) * 1e3
#print(f'Camera 0 timestamp {time_list_0} sec. Difference {diff} msec per frame')

axis[0,1].plot(diff, 'x', color='b', label='cam 1')
axis[0,1].set(ylabel='Difference between cam0 and cam1 frames [msec]')

print("Comparasion done.")
plt.show()

