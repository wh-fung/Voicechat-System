from status_type import StatusType
from chatroom import ChatroomClient, ParticipantData
from system import SystemClient
from audio import Audio
from image import Image

import asyncio
import numpy as np
import threading

from config import ENHANCEMENT


class User:
    """
    Handles user actions, and communicate between system client, chatroom client,
    GUI and audio
    """

    def __init__(self, *, sys_loop = None):
        # connections to server
        self.system_client = SystemClient(self)
        """Client to the voicechat system server"""
        self.chatroom_client = ChatroomClient(self)
        """Client to a chatroom server"""


        # peripheral control
        # audio capture and play
        self.audio = Audio()
        """Control capturing and playing of audio"""
        self.microphone = False
        """Whether the microphone is unmuted"""
        self.speaker = False
        """Whether the speaker is unmuted"""

        # webcam capture
        self.image = Image()
        """Control capturing of webcam image"""
        self.webcam = False
        """Whether the webcam is turned on"""
        self.webcam_filter = False
        """Whether the webcam filter is turned on"""

        self.sys_loop = sys_loop or asyncio.get_event_loop()

        # for updating GUI
        self.chatroom_list = None
        """List of chatrooms in the voicechat system"""
        self.chatroom_ID = None
        """ID of connected chatroom server"""
        self.participant_data = None
        """List of participants in current chatroom and their status"""
        self.recording_status = False
        """Whether a recording has been started in the chatroom"""


    async def exec(self):
        """Start the application"""
        task = asyncio.create_task(self.system_client.listener())
        await task


    @property
    def connected_server(self) -> bool:
        """Whether the user is connected to the main server"""
        return self.system_client.connected

    @property
    def connected_chatroom(self) -> bool:
        """Whether the user is currently in a chatroom"""
        return self.chatroom_client.connected


    async def connect_server(self):
        """Connect the user to the system server"""
        return await self.system_client.connect()


    async def disconnect_server(self):
        """Disconnect the user from the system server"""
        if self.connected_chatroom:
            await self.quit_chatroom()

        self.audio.close()

        return await self.system_client.disconnect()


    async def wait_chatroom_connection(self):
        """Wait until the chatroom client is connected to a chatroom server"""
        while True:
            if self.connected_chatroom: return
            await asyncio.sleep(0)


    async def create_chatroom(self):
        """Create a new chatroom"""
        if not self.connect_server: return

        if (await self.system_client.create_chatroom()) == StatusType.ERROR:
            return
        
        await self.wait_chatroom_connection()
        _ = asyncio.create_task(self.chat())


    async def join_chatroom(self, chatroom_ID: int):
        """
        Join an existing chatroom
        
        Parameters
        ------------
        chatroom_ID: int
            ID of the chatroom to be joined
        """
        if not self.connect_server: return

        if (await self.system_client.join_chatroom(chatroom_ID)) == StatusType.ERROR:
            return
        
        await self.wait_chatroom_connection()
        _ = asyncio.create_task(self.chat())


    async def quit_chatroom(self):
        """Quit a chatroom"""
        if not self.connected_chatroom: return

        await self.chatroom_client.disconnect()

        if self.microphone:
            self.microphone = False
            self.audio.stop_capturing()

        if self.speaker:
            self.speaker = False
            self.audio.stop_playing()

        if self.webcam:
            self.webcam = False
            self.webcam_filter = False
            self.image.close()

        self.participant_data = None
        self.recording_status = False


    async def request_chatroom_list(self) -> list[int]:
        """
        Get the list of existing chatrooms
        
        Returns
        ------------
        List of chatroom IDs
        """
        if not self.connected_server: return []
        
        if (await self.system_client.request_chatroom_list()) == StatusType.ERROR:
            return None

        return self.chatroom_list


    async def request_participant_data(self) -> list[tuple[int, bool]]:
        """
        Get the participant list in the current chatroom
        
        Returns
        ------------
        List of participant IDs
        """
        if not self.connected_chatroom: return []

        if (await self.chatroom_client.request_participant_data()) == StatusType.ERROR:
            return None

        return self.participant_data


    async def receive_participant_data(self, p_data: list[dict]):
        """
        Called when participant data is received from the chatroom server. Convert
        the list of data into `ParticipantData` objects, and decode the webcam images,
        if any.

        Parameters
        ------------
        p_data: list[dict]
            List of participant data
        """

        # recreate ParticipantData object
        participant_data = [ParticipantData(**p) for p in p_data]

        # decode webcam image
        for p in participant_data:
            if p.image is not None:
                p.image = np.array(p.image, dtype=np.uint8)
                p.image = Image.decode(p.image)
            
            await asyncio.sleep(0)

        self.participant_data = participant_data
        

    async def request_recording_status(self):
        """Recording recording status in the chatroom"""
        if not self.connected_chatroom: return False

        await self.chatroom_client.request_recording_status()
        return self.recording_status
    

    def capture_audio(self):
        """Capture voice input from the user, and send to chatroom server"""
        while self.connected_chatroom:
            if not self.microphone: continue

            # get audio data from client's microphone
            if (data := self.audio.capture()) is None: continue

            data = data.tolist()
            result = asyncio.run_coroutine_threadsafe(
                self.chatroom_client.send_audio_data(data), self.sys_loop)
            status = result.result()
            if status == StatusType.ERROR: break


    async def play(self, data: list):
        """Play the audio data received from server through user's speakers"""
        if not self.speaker: return

        assert isinstance(data, list)

        # play the audio data through client's speaker
        data = np.asarray(data)
        self.audio.play(data)


    def capture_image(self):
        """Capture image input from the user's webcam, and send to chatroom server"""
        while self.connected_chatroom:
            if not self.webcam: continue

            # get image data from client's webcam           
            if (image := self.image.capture()) is None: continue

            image = Image.encode(image) # encode image
            data = image.tolist() # flatten to list

            # status = await self.chatroom_client.send_image_data(data)
            result = asyncio.run_coroutine_threadsafe(
                self.chatroom_client.send_image_data(data), self.sys_loop)
            status = result.result()
            if status == StatusType.ERROR: break


    async def chat(self):
        """Handle voicechatting in a chatroom"""
        assert self.connected_chatroom

        # for receiving data from the chatroom server
        client_task = asyncio.create_task(self.chatroom_client.listener())

        # start audio capturing and playing
        self.audio.start_capturing()
        self.microphone = True
        self.audio.start_playing()
        self.speaker = True

        # start the main loops, and wait until the user disconnected
        audio_thread = threading.Thread(target=self.capture_audio, name="audio")
        if ENHANCEMENT:
            image_thread = threading.Thread(target=self.capture_image, name="image")

        audio_thread.start()
        if ENHANCEMENT: image_thread.start()

        await client_task

        # stop capturing and playing
        self.audio.stop_capturing()
        self.microphone = False
        self.audio.stop_playing()
        self.speaker = False
        audio_thread.join()

        # stop webcam capturing
        if self.webcam: self.image.close()
        self.webcam = False
        self.webcam_filter = False
        if ENHANCEMENT: image_thread.join()


    async def toggle_microphone(self):
        """Toggle mute and unmute microphone"""
        if not self.microphone:
            self.audio.start_capturing()
        else:
            self.audio.stop_capturing()

        await self.chatroom_client.toggle_microphone()

        self.microphone = not self.microphone
        return self.microphone


    async def toggle_speaker(self):
        """Toggle mute and unmute speaker"""
        if not self.speaker:
            self.audio.start_playing()
        else:
            self.audio.stop_playing()

        await self.chatroom_client.toggle_speaker()

        self.speaker = not self.speaker
        return self.speaker


    async def toggle_webcam(self):
        """Toggle on and off of webcam"""
        if not ENHANCEMENT: return False

        if self.webcam:
            self.image.close()
        else:
            self.image.open()

        await self.chatroom_client.toggle_webcam()

        self.webcam = not self.webcam
        return self.webcam


    async def toggle_filter(self):
        """Toggle webcam filter on and off"""
        if not self.webcam: return False

        if self.webcam_filter:
            print("Webcam filter turned off")
        else:
            print("Webcam filter turned on")

        self.webcam_filter = not self.webcam_filter
        return self.webcam_filter


    async def toggle_recording(self):
        """Toggle start and stop recording"""
        await self.chatroom_client.toggle_recording()
