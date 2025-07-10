# Voicechat System
A group project in my undergraduate study. A multiuser voicechat system is developed.

## Introduction
The voicechat system is set up on a main server in which all users have to connect
to it first to join the system. Users can then create a new chatroom or join an existing
chatroom by connecting themselves to the corresponding chatroom server.

In a chatroom, users can chat with and see one another. Users also have the option to
toggle their microphone, speakers, and webcams, and even start a recording in the
chatroom, in which the conversation (audio) between all members in the chatroom will be recorded.


## Instructions to Compile and Execute
Ensure that all necessary depedencies have been installed by executing:
`pip install -r requirements.txt`

The server can be started by executing: `python start_server.py`
This only has to be run once (on any device in the local network). The IP address
of the server is configured in `config.py`.

For any clients (on the same local network as the server), join the voicechat system
by executing: `python main.py`  


## Project Structure
<pre>
- util/
    Contains icon images used in GUI

- audio.py
    Handle audio capture and play on client side

- image.py
    Handle webcam image capture on client side

- filter/
    Script and resources used in applying mask filter to webcam image

- gui.py
    GUI for the voicechat system

- chatroom.py
    Handle server and client side of a chatroom instance

- system.py
    Handle server and client side of the voicechat system

- user.py
    Handle all user actions in the application

- recorder.py
    Handles audio recording, including starting and stopping the recording,
    saving the recording to a file, and denoising the recorded audio

- start_server.py
    Script to start the voicechat system server

- main.py, start_client.py
    Script to join voicechat system through a GUI

</pre>


## Project Description

### Chatroom Creation and Joining
A system server is first started, and users can join the system by connecting to
the server. The basic working principle is that a client communicates with the server
by sending events to and receiving events from it, simultaneously the system handles
these events and send corresponding replies to the client. 

The system server mainly handles the creation of and connecting clients to the chatroom
servers. When a user creates a new chatroom, a new chatroom server is started, and he
will be immediately connected to this server as the first participant. When a user joins
an existing chatroom, he will be connected to the existing server.

The creation and joining of chatrooms are only allowed if the users are not currently
in a chatroom, i.e., they have to quit the current chatroom before creating a new one
or join an existing one.


### Multiuser Voicechat

The server-client communication works under the same principle as the main system.
For each chatroom, a new chatroom server is started. Each participant who joins the
same chatroom are connected to the same server.

When a user speaks, i.e., audio is captured from his microphone, the data is sent
to the chatroom server and immediately broadcasted to other users in the chatroom
(except the sender himself, as he should not be able to listen to his own voice),
and then played through each receiving user’s speakers. When the webcam of a user
is turned on, images will be continuously captured from his webcam and sent to the
server, and everyone in the chatroom will be able to see his face through the interface.

Users have the option to toggle his microphone, speaker, and webcam. To be precise,
if the user mutes his microphone, no audio will be captured from his microphone and
sent to the server; if the user mutes his speaker, all receiving audio from the server
will not be played through his speakers; if the user turns off his webcam, no image
will be captured from his webcam and sent to the server.

The GUI is updated in real-time by continuously sending data to and receiving data
from the server through the user.


### Recording
Users can start an audio recording in the chatroom. The recording is global to all
users, i.e., only one recording can be initiated in the chatroom, and the recording
can be started and stopped by any users in the chatroom. The recording file are then
available to anyone in the chatroom (default in the directory `recording/`).
