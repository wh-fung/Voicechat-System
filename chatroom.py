from status_type import StatusType
from recorder import Recorder

import asyncio
import websockets
import json
from enum import Enum
from math import ceil

from config import HOST


class ParticipantData:
    """Status of a participant in a chatroom"""

    def __init__(self, *,
                 id: int,
                 microphone: bool = True, speaker: bool = True, webcam: bool = False,
                 image: list = None):
        self.id = id
        self.microphone = microphone
        self.speaker = speaker
        self.webcam = webcam
        self.image = image


    def __eq__(self, value: object) -> bool:
        return self.id == value.id and \
               self.microphone == value.microphone and \
               self.speaker == value.speaker and \
               self.webcam == value.webcam and \
               self.image == value.image
    

class EventType(Enum):
    """Types of events in server-client communication for chatroom"""
    (
        # client ID
        REQUEST_CLIENT_ID, CLIENT_ID,

        # for updating GUI
        REQUEST_PARTICIPANT_DATA, PARTICIPANT_DATA,
        REQUEST_RECORDING_STATUS, RECORDING_STATUS,

        # client data
        CLIENT_AUDIO_DATA, BROADCAST_AUDIO_DATA,
        CLIENT_IMAGE_DATA,

        # recording
        TOGGLE_RECORDING, RECORDING_FILE,
        
        # client status
        TOGGLE_MICROPHONE, TOGGLE_SPEAKER, TOGGLE_WEBCAM,

    ) = list(range(14))



class ChatroomServer:
    """Handles the server side of a chatroom."""

    ID = 1
    port = 8001


    def __init__(self):
        self.ID = ChatroomServer.ID
        """Chatroom ID"""
        ChatroomServer.ID += 1

        self.server = None
        """Server connection of this chatroom server"""

        self.port = ChatroomServer.port
        """Port of chatroom server"""
        ChatroomServer.port += 1

        self.participant_data = {}
        """Dict `{ClientProtocol: ParticipantData}` containing all client connections and their status"""
        self.CLIENT_ID = 1
        """ID of the next client"""

        self.recorder = Recorder()
        """Handles recording"""
        self.recording = False
        """Whether a recording has been started in this chatroom"""


    @property
    def started(self) -> bool:
        """Whether the server has started"""
        return self.server is not None


    async def start(self):
        """
        Start the chatroom server
        """
        try:
            self.server = await websockets.serve(self.handler, host=HOST, port=self.port)
        
        except ConnectionRefusedError:
            print(f"Cannot start chatroom server at port {HOST}:{self.port}")
            return StatusType.ERROR

        else:
            print(f"Chatroom server {self.ID} started at port {HOST}:{self.port}")
            return StatusType.OK
        

    async def close(self):
        """
        Close the chatroom server
        """
        if self.server is None: return StatusType.OK

        self.server.close()
        await self.server.wait_closed()

        print(f"Chatroom server at port {HOST}:{self.port} is closed")
        self.server = None
        return StatusType.OK
  

    async def handler(self, websocket: websockets.WebSocketClientProtocol):
        """
        Handles events sent from chatroom clients
        """       
        try:
            async for message in websocket:
                # read the message
                event = json.loads(message)
                event_type = EventType(event["type"])

                match event_type:
                    # send the client ID
                    case EventType.REQUEST_CLIENT_ID:
                        await self.send_ID(websocket)

                    # send the participant list
                    case EventType.REQUEST_PARTICIPANT_DATA:
                        await self.send_participant_data(websocket)

                    # broadcast received data to all clients except the sender
                    case EventType.CLIENT_AUDIO_DATA:
                        audio_data = event["data"]
                        await self.broadcast_audio_data(audio_data, websocket)
                        if self.recording:
                            self.recorder.record(audio_data) # Record the data

                    # save client webcam image data, to be shown in GUI
                    case EventType.CLIENT_IMAGE_DATA:
                        image_data = event["data"]
                        self.participant_data[websocket].image = image_data

                    # handle recording requests
                    case EventType.REQUEST_RECORDING_STATUS:
                        await self.send_recording_status(websocket)

                    case EventType.TOGGLE_RECORDING:
                        if not self.recording:
                            print("Recording started")
                        
                        else:
                            print("Recording stopped")
                            # convert the recording data to wave file
                            filename, filedata = self.recorder.convert_recording()
                            # Broadcast the recording file
                            await self.broadcast_recording(filename, filedata)

                        self.recording = not self.recording
                        

                    case EventType.TOGGLE_WEBCAM:
                        self.participant_data[websocket].webcam = \
                            not self.participant_data[websocket].webcam

                    case EventType.TOGGLE_MICROPHONE:
                        self.participant_data[websocket].microphone = \
                            not self.participant_data[websocket].microphone

                    case EventType.TOGGLE_SPEAKER:
                        self.participant_data[websocket].speaker = \
                            not self.participant_data[websocket].speaker
                        
                await asyncio.sleep(0)

            await websocket.wait_closed()

        except websockets.exceptions.ConnectionClosed:
            pass

        finally:
            # remove the client if disconnected
            self.participant_data.pop(websocket, None)

            # if the chatroom becomes empty but a recording is ongoing, stop it
            if self.recording and len(self.participant_data) == 0:
                self.recording = False
                print("Recording stopped")


    async def send_ID(self, client: websockets.WebSocketClientProtocol):
        """
        Send the client ID to a client

        Parameters:
        --------------
        client: `WebSocketClientProtocol`
        """

        event = {
            "type": EventType.CLIENT_ID.value,
            "ID": self.CLIENT_ID,
        }

        # add the client to client list
        if client not in self.participant_data:
            self.participant_data[client] = ParticipantData(id=self.CLIENT_ID)

        await client.send(json.dumps(event))
        self.CLIENT_ID += 1


    async def send_participant_data(self, client: websockets.WebSocketClientProtocol):
        """
        Send the participant list in chatroom to a client
        
        Parameters:
        --------------
        client: `WebSocketClientProtocol`
        """
        event = {
            "type": EventType.PARTICIPANT_DATA.value,
            "list": [p.__dict__ for p in self.participant_data.values()]
        }
        await client.send(json.dumps(event))


    async def send_recording_status(self, client: websockets.WebSocketClientProtocol):
        """
        Send the recording status in the chatroom to a client
        
        Parameters:
        --------------
        client: `WebSocketClientProtocol`
        """
        event = {
            "type": EventType.RECORDING_STATUS.value,
            "status": self.recording,
        }
        await client.send(json.dumps(event))


    async def broadcast_audio_data(self, data: list, sender: websockets.WebSocketClientProtocol):
        """
        Broadcast data to all clients except the sender

        Parameters
        -----------------
        data: list
            Audio data to be broadcasted

        sender: `WebSocketClientProtocol`
            The sender of the data
        """       
        event = {
            "type": EventType.BROADCAST_AUDIO_DATA.value,
            "data": data,
        }

        clients = list(self.participant_data)
        clients.remove(sender)

        if len(clients) == 0: return
        websockets.broadcast(clients, json.dumps(event))


    async def broadcast_recording(self, filename: str, filedata: str):
        """
        Broadcasts the recording file to all users. Since the file size is too large,
        it is to be sent through different chunks.
        """
        assert isinstance(filedata, str)

        CHUNK_SIZE = 1 << 19
        n_chunks = ceil(len(filedata) / CHUNK_SIZE)

        event = {
            "type": EventType.RECORDING_FILE.value,
            "filename": filename,
            "filedata": None,
            "chunk": None,
        }

        for i in range(n_chunks):
            event["filedata"] = filedata[: CHUNK_SIZE + 1]
            event["chunk"] = (i+1, n_chunks)

            filedata = filedata[CHUNK_SIZE + 1 :]
            
            websockets.broadcast(list(self.participant_data), json.dumps(event))


        print(f"Broadcasted recording file {filename}")



class ChatroomClient:
    """Handles the client side of a chatroom."""

    def __init__(self, user):
        self.ID = None
        """Client ID in a chatroom"""
        self.connection = None
        """Connection to a chatroom server"""
        self.port = None
        """Port of connected chatroom server"""

        self.user = user
        """The end user who this client belong to"""

        self.recording_file_data = ""
        """Recording file buffer"""


    @property
    def connected(self) -> bool:
        """Whether the client is connected to a server"""
        return self.connection is not None


    async def connect(self, port: int, ID: int):
        """
        Connect to a chatroom server

        Parameters
        ------------
        port: int
            Port of the chatroom server

        ID: int
            ID of the chatroom server
        """
        try:
            self.connection = await websockets.connect(f"ws://{HOST}:{port}")

        except ConnectionRefusedError:
            print(f"Cannot connect to chatroom server {ID} at port {HOST}:{port}")
            return StatusType.ERROR

        else:
            await self.request_ID()
            print(f"Connected to chatroom server {ID} at port {HOST}:{port}")
            self.user.chatroom_ID = ID
            self.port = port                
            return StatusType.OK


    async def disconnect(self):
        """
        Disconnect from a chatroom server
        """
        if not self.connected: return StatusType.OK

        await self.connection.close()

        if self.port is not None:
            print(f"Connection to chatroom server at port {HOST}:{self.port} is closed")
        
        self.connection = None
        self.port = None
        self.user.chatroom_ID = None
        self.ID = None

        return StatusType.OK
       

    async def listener(self):
        """
        Process events received from the chatroom server
        """
        while self.connected:
            try:
                async for message in self.connection:
                    event = json.loads(message)
                    event_type = EventType(event["type"])

                    match event_type:
                        # set client ID
                        case EventType.CLIENT_ID:
                            self.ID = event["ID"]

                        # play the audio data from other clients
                        case EventType.BROADCAST_AUDIO_DATA:
                            data = event["data"]
                            await self.user.play(data)

                        # get participant list
                        case EventType.PARTICIPANT_DATA:
                            data = event["list"]
                            await self.user.receive_participant_data(data)
                            
                        # get recording status
                        case EventType.RECORDING_STATUS:
                            self.user.recording_status = event["status"]

                        # save the recording file locally
                        case EventType.RECORDING_FILE:
                            self.recording_file_data += event["filedata"]
                            
                            # if all chunks have been received, write to file
                            current_chunk, total_chunk = event["chunk"]
                            if current_chunk == total_chunk:
                                await self.save_recording(event["filename"], self.recording_file_data)
                                self.recording_file_data = ""

                    await asyncio.sleep(0)
                
            except websockets.exceptions.ConnectionClosed:
                break

            else:
                await asyncio.sleep(0)


        if self.port is not None:
            print(f"Failed to receive event from chatroom server at port {HOST}:{self.port}")

        await self.disconnect()


    async def send(self, event: dict):
        """Handle data sending to the chatroom server"""
        try:
            await self.connection.send(json.dumps(event))

        except websockets.exceptions.ConnectionClosed:
            if self.port is not None:
                print(f"Failed to send event to chatroom server at port {HOST}:{self.port}")  
            
            return StatusType.ERROR
        
        except Exception as e:
            print(e)
            return StatusType.ERROR

        else:
            return StatusType.OK


    async def send_audio_data(self, data: list):
        """
        Send audio data to the chatroom server

        Parameters
        -----------
        data: list
            Audio data to be sent to the server
        """
        assert isinstance(data, list)

        event = {
            "type": EventType.CLIENT_AUDIO_DATA.value,
            "data": data,
        }
        return await self.send(event)
    

    async def send_image_data(self, data: list):
        """
        Send webcam image data to the chatroom server

        Parameters
        -----------
        data: list
            Image data to be sent to the server. Represented as a 1D list in JPG format.
        """
        assert isinstance(data, list)

        event = {
            "type": EventType.CLIENT_IMAGE_DATA.value,
            "data": data,
        }
        return await self.send(event)


    async def request_ID(self):
        """
        Send a request for the client ID in a chatroom to the chatroom server
        """
        event = {
            "type": EventType.REQUEST_CLIENT_ID.value,
        }
        return await self.send(event)


    async def request_participant_data(self):
        """Send a request for the list of participants to the chatroom server"""
        event = {
            "type": EventType.REQUEST_PARTICIPANT_DATA.value,
        }
        return await self.send(event)
        

    async def request_recording_status(self):
        """Request recording status from the chatroom server"""
        event = {
            "type": EventType.REQUEST_RECORDING_STATUS.value,
        }
        return await self.send(event)


    async def toggle_webcam(self):
        """Send a toggle webcam event to the chatroom server"""
        event = {
            "type": EventType.TOGGLE_WEBCAM.value,
        }
        return await self.send(event)


    async def toggle_microphone(self):
        """Send a toggle microphone event to the chatroom server"""
        event = {
            "type": EventType.TOGGLE_MICROPHONE.value,
        }
        return await self.send(event)


    async def toggle_speaker(self):
        """Send a toggle speaker event to the chatroom server"""
        event = {
            "type": EventType.TOGGLE_SPEAKER.value,
        }
        return await self.send(event)


    async def toggle_recording(self):
        """Send a toggle recording request to the chatroom server"""
        event = {
            "type": EventType.TOGGLE_RECORDING.value,
        }
        return await self.send(event)
    

    async def save_recording(self, filename: str, filedata: str):
        """
        Save the recording file received from the chatroom server
        """
        assert isinstance(filedata, str)

        Recorder.save_recording(filename, filedata)
        
