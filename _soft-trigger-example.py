import pypylon.pylon as pylon
import imageio.v2 as iio
import numpy as np
from PIL import Image
import time


import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
debugpy.log_to('/home/fsantoro/basler')

fps = 5  # Hz
time_to_record = 10  # seconds
images_to_grab = fps * time_to_record

tlf = pylon.TlFactory.GetInstance()
devices = tlf.EnumerateDevices()

cam = pylon.InstantCamera(tlf.CreateDevice(devices[0]))
cam.Open()

print("Using device ", cam.GetDeviceInfo().GetModelName())
cam.AcquisitionFrameRateAbs.SetValue(fps)

# Software Triggering
# Image acquisition of ONE IMAGE, starts whenever a software command is received: self.cam.ExecuteSoftwareTrigger()

# "Frame Start": The camera initializes the acquisition of one image.
# If the Exposure Start trigger is enabled, the camera is now ready to receive Exposure Start trigger signals.
# If the Exposure Start trigger is not available or disabled, the camera automatically starts exposing the image. 
# Note that in this case, exposure starts with a delay (see exposure start delay).
#
# "Frame End": The camera finalizes the acquisition of one image.
# If this trigger is disabled or not available, the camera automatically finalizes image acquisition after exposure.
#
# "Frame Active": When the trigger signal rises, the camera generates a Frame Start trigger signal. When the trigger signal falls, 
# the camera generates a Frame End trigger signal. You can change this behavior by setting the trigger activation mode.

cam.TriggerSelector.SetValue('FrameStart')
cam.TriggerSource.SetValue('Software')
cam.TriggerMode.SetValue('On')

#writer = iio.get_writer('output-filename.mkv',  fps=fps,  codec='libx264')

print(f"Recording {time_to_record} second video at {fps} fps")
cam.StartGrabbing()
img_sum=np.zeros((cam.Height.Value, cam.Width.Value), dtype=np.uint8)

frame_index = 0
while frame_index < images_to_grab:
    print("Executing Software Trigger")
    cam.ExecuteSoftwareTrigger()
    res = cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
    fpsi = res.BlockID
    print(fpsi, end='\r')
        
    if res.GrabSucceeded():
        resArray = res.Array
        print(resArray)
        img = Image.fromarray(res.Array)
        img.save(f'image{fpsi}.png')
        res.Release()
    else:
        print("Grab failed, stopping")
        cam.StopGrabbing()
    
    frame_index = fpsi
    time.sleep(1)
    
print("Saving...")
cam.StopGrabbing()
cam.Close()

print("Done")

