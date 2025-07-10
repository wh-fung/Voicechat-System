from status_type import StatusType

from filter import filtering

import cv2
import numpy as np
import threading


class Image:

    def __init__(self):
        self.device = None


    def open(self):
        """Turn on the webcam"""
        self.device = cv2.VideoCapture(0) # default webcam device

        if self.device.isOpened():
            print("Webcam turned on")
            return StatusType.OK
        else:
            print("Failed to open webcam")
            return StatusType.ERROR


    def close(self):
        """Turn off the webcam"""
        if self.device is None: return

        self.device.release()
        self.device = None
        print("Webcam turned off")


    def capture(self, filtered: bool = False):
        """
        Capture a frame from the webcam

        Parameters
        ------------------       
        filtered: bool, default = `False`
            If true, apply the mask filter to the captured image
        """
        if self.device is None: return None

        status, frame = self.device.read()
        if not status:
            print("Failed to capture frame")
            return None

        frame = cv2.resize(frame, (640, 480)) # lower frame resolution
        frame = cv2.flip(frame, 1) # flip the frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # convert to RGB

        if filtered and (filtered_frame := filtering(frame)) is not None:
            return filtered_frame
        
        return frame


    @staticmethod
    def encode(frame: np.ndarray, *, ext: str = ".jpg") -> np.ndarray | StatusType:
        """Encode a captured frame, default JPG"""
        status, encoded_frame = cv2.imencode(ext, frame) # encode to JPG
        if not status:
            print("Cannot encode frame")
            return StatusType.ERROR
        return encoded_frame


    @staticmethod
    def decode(frame: np.ndarray, *, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
        """Decode a frame to RGB image"""
        return cv2.imdecode(frame, flags)

