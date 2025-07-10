from status_type import StatusType
from chatroom import ChatroomServer

import asyncio
import websockets
import json
from enum import Enum

from config import HOST


class EventType(Enum):
    """Types of events in server-client communication for voicechat system"""
    (
    CREATE_CHATROOM,
    JOIN_CHATROOM,
    CHATROOM_PORT,
    GET_CHATROOM_LIST, CHATROOM_LIST,
    ) = list(range(5))


class SystemServer:
    """Handles the server side of the voicechat system"""

    port = 8000
       

    def __init__(self):
        self.server = None
        self.chatroom_list = {}


    @property
    def started(self) -> bool:
        """Whether the server has started"""
        return self.server is not None
    

    async def start(self):
        """Start the server"""
        try:
            self.server = await websockets.serve(self.handler, host=HOST, port=SystemServer.port)
        
        except ConnectionRefusedError:
            print(f"Cannot start system server at port {HOST}:{SystemServer.port}")
            return StatusType.ERROR

        else:
            print(f"System server started at port {HOST}:{SystemServer.port}")
            return StatusType.OK


    async def close(self):
        """
        Close the server
        """
        if not self.started: return StatusType.OK

        self.server.close()
        await self.server.wait_closed()

        print(f"System server at port {HOST}:{SystemServer.port} is closed")
        self.server = None
        return StatusType.OK


    async def handler(self, websocket: websockets.WebSocketClientProtocol):
        """
        Handles events sent from clients
        """
        try:
            async for message in websocket:
                event = json.loads(message)
                event_type = EventType(event["type"])
                match event_type:
                    # create a chatroom, then join the client
                    case EventType.CREATE_CHATROOM:
                        if (chatroom_ID := await self.create_chatroom()) == StatusType.ERROR:
                            continue
                        await self.join_chatroom(websocket, chatroom_ID)
                
                    # join the client to an existing chatroom by ID
                    case EventType.JOIN_CHATROOM:
                        await self.join_chatroom(websocket, event["chatroom_ID"])

                    # send the chatroom list to a client
                    case EventType.GET_CHATROOM_LIST:
                        await self.send_chatroom_list(websocket)

                await asyncio.sleep(0)

        except websockets.exceptions.ConnectionClosed:
            return


    async def create_chatroom(self) -> int:
        """
        Create a new chatroom server
        
        Returns
        -----------
        ID of the created chatroom
        """
        # create new chatroom server
        chatroom_server = ChatroomServer()
        
        # start the chatroom server
        if (await chatroom_server.start()) == StatusType.ERROR:
            return StatusType.ERROR

        # add chatroom to list
        self.chatroom_list[chatroom_server.ID] = chatroom_server  
        return chatroom_server.ID


    async def join_chatroom(self, client: websockets.WebSocketClientProtocol, chatroom_ID: int):
        """
        Connect a client to a chatroom server by chatroom ID
        
        Parameters
        ---------------
        client: WebSocketClientProtocol

        chatroom_ID: int
            ID of the chatroom to be connected to
        """

        # retrieve port of chatroom server from ID
        chatroom_server = self.chatroom_list[chatroom_ID]
        port = chatroom_server.port

        # send the port to the client
        event = {
            "type": EventType.CHATROOM_PORT.value,
            "port": port,
            "ID": chatroom_ID,
        }

        await client.send(json.dumps(event))


    async def send_chatroom_list(self, client):
        """Send the chatroom list to a client"""
        event = {
            "type": EventType.CHATROOM_LIST.value,
            "list": list(self.chatroom_list.keys()),
        }
        await client.send(json.dumps(event))



class SystemClient():
    """Handles the client side of the voicechat system"""

    def __init__(self, user):
        self.connection = None
        """Connection to the main system"""
        self.user = user
        """The end user who this client belong to"""


    @property
    def connected(self) -> bool:
        """Whether the client is connected to the system server"""
        return self.connection is not None


    async def connect(self):
        """Connect to the system server"""
        try:
            self.connection = await websockets.connect(f"ws://{HOST}:{SystemServer.port}")

        except ConnectionRefusedError:
            print(f"Cannot connect to system server at port {HOST}:{SystemServer.port}")
            return StatusType.ERROR

        else:
            print(f"Connected to system server at port {HOST}:{SystemServer.port}")
            return StatusType.OK


    async def disconnect(self):
        """Disconnect from the system server"""
        if not self.connected: return StatusType.OK

        await self.connection.close()

        print(f"Connection to system server at port {HOST}:{SystemServer.port} is closed")
        self.connection = None
        return StatusType.OK


    async def listener(self):
        """Process events received from the system server"""

        while self.connected:
            try:
                async for message in self.connection:
                    event = json.loads(message)
                    event_type = EventType(event["type"])

                    match event_type:
                        # connect the client to a chatroom server after receiving its
                        # port from the system server
                        case EventType.CHATROOM_PORT:
                            await self.user.chatroom_client.connect(event["port"], event["ID"]) 
                        
                        # retrieve the chatroom list from the server
                        case EventType.CHATROOM_LIST:
                            self.user.chatroom_list = event["list"]
                            
                    await asyncio.sleep(0)

            except websockets.exceptions.ConnectionClosed:
                break
            
            except Exception as e:
                print(e)

            else:
                await asyncio.sleep(0)


        print(f"Failed to communicate with system server at port {HOST}:{SystemServer.port}")
        await self.disconnect()


    async def send(self, event: dict):
        """Handle data sending to the system server"""
        try:
            await self.connection.send(json.dumps(event))

        except websockets.exceptions.ConnectionClosed:
            print(f"Failed to communicate with system server at port {HOST}:{SystemServer.port}")
            return StatusType.ERROR

        except Exception as e:
            print(e)
            return StatusType.ERROR

        else:
            return StatusType.OK


    async def request_chatroom_list(self) -> list[int]:
        """
        Send a request of getting the list of existing chatrooms to the system server

        Returns
        ----------
        List of chatroom IDs
        """
        if not self.connected: return None

        event = {
            "type": EventType.GET_CHATROOM_LIST.value,
        }

        if (await self.send(event)) == StatusType.ERROR:
            print("Failed to get chatroom list")
            return None
        
    
    async def create_chatroom(self):
        """
        Send a request of creating a chatroom to the system server
        """
        event = {
            "type": EventType.CREATE_CHATROOM.value,
        }

        if (await self.send(event)) == StatusType.ERROR:
            print("Failed to create chatroom")
            return StatusType.ERROR
        
        return StatusType.OK


    async def join_chatroom(self, chatroom_ID: int):
        """
        Send a request of joining a chatroom to the server

        Parameters
        ------------
        chatroom_ID: int
            ID of the chatroom to be joined
        """
        event = {
            "type": EventType.JOIN_CHATROOM.value,
            "chatroom_ID": chatroom_ID,
        }

        if (await self.send(event)) == StatusType.ERROR:
            return StatusType.ERROR
        
        return StatusType.OK
    
