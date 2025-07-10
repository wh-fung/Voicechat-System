import tempfile
import queue
import datetime
import numpy as np

import wave
import noisereduce as nr
import base64


class Recorder:

    def __init__(self, channels=2, rate=44100):
        self.channels = channels
        self.rate = rate

        self.buffer = queue.Queue()


    def record(self, data: list):
        """Put the audio into buffer"""
        assert isinstance(data, list)

        try:
            data = np.array(data).flatten()
            self.buffer.put_nowait(data.copy())

        except self.buffer.Full:
            return


    def convert_recording(self):
        """
        Convert the recorded audio data to wave file encoded in base64

        Returns
        ---------
        filename: str
            Filename of the wave file

        filedata: str
            Binary wave file encoded in base64
        """

        filename = tempfile.mktemp(
            prefix=datetime.datetime.now().strftime('%Y%m%d%H%M%S'), # Ensure the filename is unique
            suffix='.wav',
            dir='recording',
        ) 

        filedata = bytes()
        recording_data = np.empty((0))

        while not self.buffer.empty():
            data = self.buffer.get_nowait()
            recording_data = np.concatenate((recording_data, data))

        if (size := recording_data.shape[0]) == 0:
            return None

        # Normalize the audio data
        recording_data = np.int16(
            recording_data / np.max(np.abs(recording_data)) * 32767
        )

        # Write the RIFF header
        filedata += (b'RIFF')
        filedata += ((36 + 2 * size).to_bytes(4, 'little'))  # ChunkSize
        filedata += (b'WAVE')

        # Write the format subchunk (fmt chunk)
        filedata += (b'fmt ')
        filedata += ((16).to_bytes(4, 'little'))  # Subchunk1Size
        filedata += ((1).to_bytes(2, 'little'))  # AudioFormat
        filedata += ((self.channels).to_bytes(2, 'little'))  # NumChannels
        filedata += ((self.rate).to_bytes(4, 'little'))  # SampleRate
        filedata += ((self.rate * 2).to_bytes(4, 'little'))  # ByteRate
        filedata += ((2).to_bytes(2, 'little'))  # BlockAlign
        filedata += ((16).to_bytes(2, 'little'))  # BitsPerSample

        # Write the data subchunk header
        filedata += (b'data')
        filedata += ((2 * size).to_bytes(4, 'little'))  # Subchunk2Size

        # Write the audio data
        filedata += recording_data.tobytes()

        filedata_str = base64.b64encode(filedata).decode("utf-8")

        return filename, filedata_str


    @staticmethod
    def save_recording(filename: str, filedata_str: str):
        """
        Save a wave file locally

        Parameters
        -------------
        filename: str
            Filename of the wave file

        filedata: str
            Binary data of the wave file encoded in base64 
        """

        filedata = base64.b64decode(filedata_str)

        with open(filename, "wb") as f:
            f.write(filedata)

        print("Saved recording file", filename)

        # denoise the audio
        # Recorder.denoise_audio(filename, filename + "_denoised")


    ### under progress
    @staticmethod
    def denoise_audio(source_file, target_file):
        with wave.open(source_file, 'rb') as audio_file:
            sample_w = audio_file.getsampwidth()
            sample_r = audio_file.getframerate()
            num_ch = audio_file.getnchannels()
            num_fr = audio_file.getnframes()

            audio_d = np.frombuffer(audio_file.readframes(num_fr), dtype=np.int16)

        if num_ch > 1:
            audio_d = np.reshape(audio_d, (num_fr, num_ch))

        denoised_audio = nr.reduce_noise(audio_d)

        with wave.open(target_file, 'wb') as processed_audio_file:
            processed_audio_file.setsampwidth(sample_w)
            processed_audio_file.setframerate(sample_r)
            processed_audio_file.setnchannels(num_ch)

            processed_audio_file.writeframes(denoised_audio.tobytes())

