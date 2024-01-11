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
            'path': ':ACQ_MODE',
            'type': 'text',
            'value': 'CONTINUOUS',
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Basler Acquisition Mode',
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
            'path': ':TRIGGER:DELAY',
            'type': 'numeric',
            'value': 0,
            'options': ('no_write_shot',),
            # 'ext_options': {
            #     'tooltip': 'Trigger source. ',
            # },
        },
        {
            'path': ':TRIGGER:TRIG_ID',
            "type": "text",
            "value": "^START$",
            "options": ("no_write_shot",),
            "help": "WRTD ID regex to wait for",
            # 'ext_options': {
            #     'tooltip': 'Incoming message us to trigger. These options will contain the trigger timestamp, use to trigger the camera',
            # },
        },
        {
            'path': ':STDOUT',
            "type": "text",
            "options": ("no_write_model","write_once"),
            "help": "standard output of forked process",
            # 'ext_options': {
            #     'tooltip': 'Incoming message us to trigger. These options will contain the trigger timestamp, use to trigger the camera',
            # },
        },
        {
            'path': ':STDERR',
            "type": "text",
            "options": ("no_write_model","write_once"),
            "help": "standard error of forked process",
            # 'ext_options': {
            #     'tooltip': 'Incoming message us to trigger. These options will contain the trigger timestamp, use to trigger the camera',
            # },
        },
        {
            'path': ':PID',
            "type": "numeric",
            "options": ("no_write_model","write_once"),
            "help": "process id of forked process",
            # 'ext_options': {
            #     'tooltip': 'Incoming message us to trigger. These options will contain the trigger timestamp, use to trigger the camera',
            # },
        },
        {
            'path': ':TIMEOUT',
            "type": "numeric",
            "value" : 40,
            "options": ("no_write_shot"),
            "help": "timeout in seconds",
            # 'ext_options': {
            #     'tooltip': 'Incoming message us to trigger. These options will contain the trigger timestamp, use to trigger the camera',
            # },
        },

        {
            'path': ':INIT_ACTION',
            'type': 'action',
            'valueExpr': "Action(Dispatch('MDSIP_SERVER','INIT',50,None),Method(None,'FORK_STREAM',head))",
            'options': ('no_write_shot',),
        },
        {
            'path': ':STREAM',
            'type': 'any',
            # 'ext_options': {
            #     'tooltip': '',
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

    """
    Class to wait until a delay after (or before) a time specified by
    a WRTD timing system message
    """

    class StreamWriter(threading.Thread):
        def __init__(self, reader):
            super(ACA800.StreamWriter, self).__init__(name="StreamWriter")
            self.tree_name = reader.device.tree.name
            self.tree_shot = reader.device.tree.shot
            self.node_path = reader.device.path
            self.reader = reader

        def run(self):
            import sys
            try:
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)
                
                input_node = self.device.getNode(f"FRAMES")

                delta_time = float(1.0 / self.device.FPS.data())
                time_at_0 = self.device.TRIGGER.TIME_AT_0.data()

                event_name = self.device.STREAM.EVENT_NAME.data()
             
                frame_index = 0
                while True:
                    result = None
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

                    input_node.makeSegment(begin, end, dim, result)
                    
                    benchmark_end = time.time()
                    benchmark_elapsed = benchmark_end - benchmark_start

                    frame_index += 1
                    self.device._log_info(f"Finished writing frame {frame_index}/{self.reader.frames_to_grab}, took {benchmark_elapsed}s")

                    MDSplus.Event(event_name)
            except Exception as e:
                self.exception = e
                traceback.print_exc()
            sys.exit()
            return

    class StreamReader(threading.Thread):
        
        def __init__(self, device):
            super(ACA800.StreamReader, self).__init__(name="StreamReader")
            self.tree_name = device.tree.name
            self.tree_shot = device.tree.shot
            self.node_path = device.path


        def run(self):
            import sys
            try:
                import pypylon.pylon as pylon
                from datetime import datetime, timezone
                from ctypes import cdll, c_char_p, c_double, c_int
                
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)
                
                self.frame_queue = queue.Queue()
                                
                self.time_to_record = int(self.device.RUNNING_TIME.data())  # seconds
                self.frames_to_grab = int(self.device.FPS.data()) * self.time_to_record

                self.trigger_id = self.device.TRIGGER.TRIG_ID.data()
                self.delay = self.device.TRIGGER.DELAY.data()

                wrtdListen = cdll.LoadLibrary("libwrtdListen.so")
                self.wrtdGetDTacqTime = wrtdListen.wrtdGetDTacqTime
                self.wrtdGetDTacqTime.argtypes = [c_char_p, c_double, c_int]
                self.wrtdGetDTacqTime.restype = c_double
                                                
                #######################################################################################################################
                #Setting up and Configuring the camera using its IP address:
                ip_address = self.device.ADDRESS.data()
                info = pylon.DeviceInfo()
                info.SetPropertyValue('IpAddress', ip_address)
                
                tlFactory = pylon.TlFactory.GetInstance()
                
                self.cam = pylon.InstantCamera(tlFactory.CreateFirstDevice(info))
                self.cam.Open()
                
                self.device._log_info(f"Using device {self.cam.GetDeviceInfo().GetModelName()}")
                
                #Set Height and Width               
                HEIGHT = int(self.device.HEIGHT.data())
                WIDTH = int(self.device.WIDTH.data())

                self.cam.Height =  HEIGHT
                self.cam.Width = WIDTH

                self.device._log_info((f'Cameras resolution set to height {HEIGHT} and width {WIDTH}'))

                #Enable PTP for this camera
                self.cam.GevIEEE1588 = True
                
                #Acquisition Mode (ACQ_MODE):
                self.cam.AcquisitionMode = str(self.device.ACQ_MODE.data()).title()
                    
                #Set the FPS
                self.cam.AcquisitionFrameRateEnable.SetValue(True)
                self.cam.AcquisitionFrameRateAbs.SetValue(float(self.device.FPS.data()))
                
                timestamp = self.wrtdGetDTacqTime(self.trigger_id.encode(), float(self.delay), 1)
                actionTime = int(timestamp * 1e9)
                
                self.device._log_info(f'Received trigger message, with payload = {actionTime}')

                self.cam.GevTimestampControlLatch()
                currentTimestamp = self.cam.GevTimestampValue()
                self.device._log_info(f'Current Camera Timestamp is {currentTimestamp}')

                if currentTimestamp >= actionTime:
                    print("Warning: Trigger is in the past. Exiting.")
                    self.cam.Close()
                    exit()
                    
                #Triggering using SyncFreeRun timer: 
                # https://docs.baslerweb.com/synchronous-free-run#converting-the-64-bit-timestamp-to-start-time-high-and-start-time-low

                self.cam.SyncFreeRunTimerStartTimeLow = (actionTime & 0x00000000FFFFFFFF)
                self.cam.SyncFreeRunTimerStartTimeHigh = (actionTime & 0xFFFFFFFF00000000) >> 32
                
                self.cam.SyncFreeRunTimerUpdate()
                self.cam.SyncFreeRunTimerEnable = True

                self.device._log_info(
                    f"It will be recording {self.time_to_record} second video at {self.device.FPS.data()} fps. Max #Images = {self.frames_to_grab}")
                #######################################################################################################################

                self.writer = self.device.StreamWriter(self)
                self.writer.setDaemon(True)
                self.writer.start()

                self.cam.StartGrabbing()

                last_frame_id = 0
                frame_index = 0
                while self.device.RUNNING.on and frame_index < self.frames_to_grab:
                    try:
                        # Parameters for cam.RetrieveResult():
                        # timeoutMs - A timeout value in ms for waiting for a grab result, or INFINITE (0xFFFFFFFF) value.
                        # grabResult - Receives the grab result.
                        # timeoutHandling - If timeoutHandling equals TimeoutHandling_ThrowException, a timeout exception is thrown on timeout.
                        
                        #grabResult = self.cam.RetrieveResult(10000, pylon.TimeoutHandling_ThrowException)
                        grabResult = self.cam.RetrieveResult(0xFFFFFFFF, pylon.TimeoutHandling_ThrowException)
                        
                    except Exception as e:
                        print('got an exception ', e, 'frame_index = ', frame_index)
                        self.device._log_info(e)
                        self.frame_queue.put(None) # signal the end of data acquisition
                        break
                    
                    if not grabResult:
                        print('Did not get a result', e, 'frame_index = ', frame_index)
                        break
                    
                    if grabResult.GrabSucceeded():
                        frame_index += 1
                        
                        missed_frames = grabResult.GetID() - last_frame_id - 1
                        last_frame_id = grabResult.GetID()
                        
                        if missed_frames > 0:
                            print("Missed", missed_frames, "frames.")
                        
                        timestamp = datetime.fromtimestamp(grabResult.GetTimeStamp() / float(1e9), timezone.utc)

                        self.device._log_info(f"Timestamp {timestamp}")
                        
                        self.frame_queue.put(np.array([grabResult.Array]))
                        grabResult.Release()
                    else:
                        print('The GRAB Failed', frame_index)
                        break
                            
                # else:
                #     pass

            except Exception as e:
                self.exception = e
                traceback.print_exc()


            # This will signal the StreamWriter that no more buffers will be coming
            self.frame_queue.put(None)
            
            self.device.RUNNING.on = False
            self.cam.StopGrabbing()
            self.cam.DestroyDevice()
            self.cam.Close()
            del(self.cam)
            del(tlFactory)
            del(pylon)
            self.writer.join()
            self.writer = None
            sys.exit()
            # Wait for the StreamWriter to finish
            #try:
            #    while self.writer.is_alive():
            #        pass
            #finally:
            #    self.writer.join()
            #    if hasattr(self.writer, "exception"):
            #        self.exception = self.writer.exception
   
    
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
        thread.setDaemon(True)
        thread.start()
        thread.join()
    
    START_STREAM = start_stream

    def fork_stream(self):
        import os
        import subprocess
        timeout = float(self.TIMEOUT)
        script = f"{os.path.realpath(os.path.dirname(__file__))}/stream-basler.sh"
        proc = subprocess.run([script, self.tree.name, str(self.tree.shot), self.path], capture_output=True, text=True, timeout=timeout)
        self.STDOUT.record = proc.stdout
        self.STDERR.record = proc.stderr
        if proc.returncode != 0:
            raise Exception(f"Failed to fork stream: {proc.stderr}")
    FORK_STREAM = fork_stream

    def stop_stream(self):
        self.RUNNING.on = False

    STOP_STREAM = stop_stream
