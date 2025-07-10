import sounddevice as sd
import queue
from enum import Enum


class DeviceType(Enum):
    """Constant literals for audio device types"""
    INPUT, OUTPUT = list(range(2))


class AudioDevice:
    """Handles audio devices"""

    def __init__(self, device_type):
        self.device = None
        if device_type == DeviceType.INPUT:
            self._info = sd.query_devices(self.device, "input")
            self.sample_rate = int(self._info["default_samplerate"])
            self.channels = int(self._info["max_input_channels"])
            print("Initialize input device", self._info["name"])

        else:
            self._info = sd.query_devices(self.device, "output")
            self.sample_rate = int(self._info["default_samplerate"])
            self.channels = int(self._info["max_output_channels"])
            print("Initialize output device", self._info["name"])
        


class Audio:
    """Handles audio capture and play"""

    ### private

    def _callback(self, indata, frames, time, status):
        """Callback function during capture"""

        if status: print(status)

        # copy captured audio data from device buffer
        data = indata.copy()
        try:
            self._input_buffer.put_nowait(data)
        except queue.Full:
            return


    def _playback(self, outdata, frames, time, status):
        """Callback function during playback"""

        if status: print(status)

        # copy playback audio data to device output
        try:
            outdata[:frames] = self._output_buffer.get_nowait()
        except queue.Empty:
            outdata = []



    ### public
            
    def __init__(self):
        """Initialize input and output devices"""

        self._input_device = AudioDevice(DeviceType.INPUT)
        self._input_stream = sd.InputStream(
            device = self._input_device.device,
            samplerate = self._input_device.sample_rate,
            channels = self._input_device.channels,
            callback = self._callback,
        )
        self._input_buffer = queue.Queue()

        self._output_device = AudioDevice(DeviceType.OUTPUT)
        self._output_stream = sd.OutputStream(
            device = self._output_device.device,
            samplerate = self._output_device.sample_rate,
            channels = self._output_device.channels,
            callback = self._playback,
        )
        self._output_buffer = queue.Queue()


    def start_capturing(self):
        self._input_stream.start()
        print("Microphone unmuted")


    def stop_capturing(self):
        self._input_stream.stop()
        print("Microphone muted")


    def start_playing(self):
        self._output_stream.start()
        print("Speaker unmuted")


    def stop_playing(self):
        self._output_stream.stop()
        print("Speaker muted")


    def capture(self):
        """Capture audio from microphone"""
        try:
            data = self._input_buffer.get_nowait()
            return data
        except queue.Empty:
            return None


    def play(self, data):
        """Play audio data through speaker"""
        try:
            self._output_buffer.put_nowait(data)
        except queue.Full:
            return


    def close(self):
        """Close the input and output stream"""
        self._input_stream.close()
        self._output_stream.close()
        print("Audio streams closed")

