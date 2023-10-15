import traceback
import MDSplus
import numpy as np
import threading
import time
import queue

class ACA800(MDSplus.Device):
    '''
    # Basler ACE ACA800 Device Driver
    '''

    parts = [
        {
            'path': ':COMMENT',
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':MODE',
            'type': 'text',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'The intended mode of operation.',
            #     #'values': _MODE_OPTIONS,
            # },
        },
        {
            'path': ':ADDRESS',
            'type': 'text',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'IP address or DNS name of the camera.',
            # },
        },           
        {
            'path': ':FRAMES',
            'type': 'signal',
            'options': ('no_write_model', 'write_once',)
        },
        
        {
            'path': ':FIRMWARE',
            'type': 'text',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Firmware version of the Basler Cam.',
            # },
        },
        {
            'path': ':FPS',
            'type': 'numeric',
            'value': 5,
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Frame Sample FPS in Hertz.',
            # },
        },       
        {
            'path': ':HEIGHT',
            'type': 'numeric',
            'value': 640,
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Default image width, which can be overridden per-input.',
            #     'min': 1,
            # },
        },
        {
            'path': ':WIDTH',
            'type': 'numeric',
            'value': 600,
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Default image width, which can be overridden per-input.',
            #     'min': 1,
            # },
        },
        {
            'path': ':RUNNING_TIME',
            'type': 'numeric',
            'value': 10,
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Default image width, which can be overridden per-input.',
            #     'min': 1,
            # },
        }, 
        {
            'path': ':RUNNING',
            'type': 'numeric',
            # 'on': False,
            'options': ('no_write_model',),
            # 'ext_options': {
            #     'tooltip': 'On if running, or Off otherwise.',
            # },
        },
        {
            'path': ':TRIGGER',
            'type': 'any',
        },
        {
            'path': ':TRIGGER:TIMESTAMP', # Or TIME_OF_DAY
            'type': 'numeric',
            'options': ('write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Recorded trigger time as a UNIX timestamp in seconds.',
            # },
        },
        {
            'path': ':TRIGGER:TIME_AT_0',
            'type': 'numeric',
            'value': 0,
            'options': ('write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Time offset in seconds, used when building the Window(start, end, TIME_AT_0)',
            # },
        },
        {
            'path': ':TRIGGER:SOURCE',
            'type': 'text',
            'value': 'SOFT',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Trigger source. These options will decide if the timing highway is d0 or d1. For a soft trigger use STRIG, and for a hard trigger use EXT.',
            # },
        },
        {
            'path': ':INIT_ACTION',
            'type': 'action',
            'valueExpr': "Action(Dispatch('MDSIP_SERVER','INIT',50,None),Method(None,'INIT',head,'auto'))",
            'options': ('no_write_shot',),
        },
        {
            'path': ':STREAM',
            'type': 'any',
            # 'ext_options': {
            #     'tooltip': 'Contains settings for use with MODE=STREAM.',
            # },
        },
        {
            'path': ':STREAM:EVENT_NAME',
            'type': 'text',
            'value': 'STREAM',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Name of the event generated whenever a segment is captured.',
            # },
        },
     
    ]
    
 
    def _init(self):
        pass

    class StreamWriter(threading.Thread):
        def __init__(self, reader):
            super(ACA800.StreamWriter, self).__init__(name="StreamWriter")
            self.tree_name = reader.device.tree.name
            self.tree_shot = reader.device.tree.shot
            self.node_path = reader.device.path
            self.reader = reader

        def run(self):
            try:
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)
                
                input_node = self.device.getNode(f"FRAMES")

                delta_time = float(1.0 / self.device.FPS.data())
                time_at_0 = self.device.TRIGGER.TIME_AT_0.data()

                event_name = self.device.STREAM.EVENT_NAME.data()
             
                frame_index = 0
                while True:
                    try:
                        result = self.reader.frame_queue.get(block=True, timeout=1)
                    except queue.Empty:
                        continue

                    # A buffer of None signals the end to streaming
                    if result is None:
                        break

                    benchmark_start = time.time()
                    
                    begin = (frame_index * delta_time)
                    end = begin + delta_time
                    dim = MDSplus.Range(begin, end, delta_time)

                    input_node.makeSegment(begin, end, dim, result.Array)
                    result.Release()
                    
                    benchmark_end = time.time()
                    benchmark_elapsed = benchmark_end - benchmark_start

                    frame_index += 1
                    self.device._log_info(f"Finished writing frame {frame_index}/{self.reader.frames_to_grab}, took {benchmark_elapsed}s")

                    MDSplus.Event(event_name)

            except Exception as e:
                self.exception = e
                traceback.print_exc()


    class StreamReader(threading.Thread):
        
        def __init__(self, device):
            super(ACA800.StreamReader, self).__init__(name="StreamReader")
            self.tree_name = device.tree.name
            self.tree_shot = device.tree.shot
            self.node_path = device.path

        def run(self):
            try:
                import pypylon.pylon as pylon
                from datetime import datetime, timezone
            
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)
                
                self.frame_queue = queue.Queue()
                
                self.time_to_record = int(self.device.RUNNING_TIME.data())  # seconds
                self.frames_to_grab = int(self.device.FPS.data()) * self.time_to_record

                tlFactory = pylon.TlFactory.GetInstance()
                
                self.cam = pylon.InstantCamera(tlFactory.CreateFirstDevice())
                #     self.camera.AcquisitionMode.SetValue('SingleFrame')   # 'SingleFrame' or 'Continuous'
                self.cam.Open()
                
                self.device._log_info(f"Using device {self.cam.GetDeviceInfo().GetModelName()}")
                      
                #Set the FPS
                self.cam.AcquisitionFrameRateEnable.SetValue(True)
                self.cam.AcquisitionFrameRateAbs.SetValue(float(self.device.FPS.data()))
                self.cam.MaxNumBuffer = 1900
                self.cam.OutputQueueSize = 1900


                #self.writer = self.device.StreamWriter(self)
                #self.writer.setDaemon(True)
                #self.writer.start()

                self.device._log_info(f"Recording {self.time_to_record} second video at {self.device.FPS.data()} fps. Max #Images = {self.frames_to_grab}")
                                      
                #self.cam.StartGrabbingMax(self.frames_to_grab, pylon.GrabStrategy_OneByOne)
                self.cam.StartGrabbing(pylon.GrabStrategy_UpcomingImage)
                
                last_frame_id = 0
                frame_index = 0
                while self.device.RUNNING.on and frame_index < self.frames_to_grab:
                    try:
                        # Parameters for cam.RetrieveResult():
                        # timeoutMs - A timeout value in ms for waiting for a grab result, or INFINITE (inf) value.
                        # grabResult - Receives the grab result.
                        # timeoutHandling - If timeoutHandling equals TimeoutHandling_ThrowException, a timeout exception is thrown on timeout.
                        
                        # In pypylon could the following values for infinite:
                        # >>> import pypylon.pylon as py
                        # >>> py.waitForever
                        # 4294967295
                        # >>> hex(py.waitForever)
                        # '0xffffffff'
                        # >>>
                        
                        grabResult = self.cam.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
                    except e:
                        print(e)
                        self.frame_queue.put(None) # signal the end of data acquisition
                        break
                    
                    if not grabResult:
                        continue
                    
                    if grabResult.GrabSucceeded():
                        frame_index += 1
                        
                        missed_frames = grabResult.GetID() - last_frame_id - 1
                        last_frame_id = grabResult.GetID()
                        
                        if missed_frames > 0:
                            print("Missed", missed_frames, "frames.")
                        
                        timestamp = datetime.fromtimestamp(grabResult.GetTimeStamp() / float(1e9), timezone.utc)

                        print("Timestamp", timestamp)
                        
                        self.frame_queue.put(grabResult)                        
                            
                # else:
                #     pass

            except Exception as e:
                self.exception = e
                traceback.print_exc()


            # This will signal the StreamWriter that no more buffers will be coming
            self.frame_queue.put(None)
            
            self.writer = self.device.StreamWriter(self)
            self.writer.setDaemon(True)
            self.writer.start()
            
            self.device.RUNNING.on = False
            self.cam.StopGrabbing()
            self.cam.Close()
            
            # Wait for the StreamWriter to finish
            try:
                while self.writer.is_alive():
                    pass
            finally:
                self.writer.join()
                if hasattr(self.writer, "exception"):
                    self.exception = self.writer.exception
   
    
    #Helper Methods
    def _log_verbose(self, format, *args):
        self.dprint(4, format, *args)
    
    def _log_info(self, format, *args):
        self.dprint(3, format, *args)
        
    def _log_warning(self, format, *args):
        self.dprint(2, format, *args)

    def _log_error(self, format, *args):
        self.dprint(1, format, *args)
    
    ###
    ### Streaming Methods
    ###

    def start_stream(self):

        self.RUNNING.on = True

        thread = self.StreamReader(self)
        thread.start()
        thread.join()

    START_STREAM = start_stream

    def stop_stream(self):
        self.RUNNING.on = False

    STOP_STREAM = stop_stream
