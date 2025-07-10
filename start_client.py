from status_type import StatusType
from user import User
from gui import *

import sys
import asyncio
import threading

from PyQt5.QtWidgets import QApplication


async def connect(user):
    """Connect the user to the server"""
    return await user.connect_server()


async def exec(user, qapp):
    """Hold the connection of the user to the server"""
    await user.exec()
    qapp.quit() # if the server closes prematurely, close the GUI


async def disconnect(user):
    """Disconnect the user from the server"""
    return await user.disconnect_server()


async def main():

    # set up a backend thread for server-client communication
    sys_loop = asyncio.new_event_loop()
    sys_thread = threading.Thread(target=sys_loop.run_forever, name="sys")

    sys_thread.start()

    # connect user to voicechat system server
    user = User(sys_loop=sys_loop)

    future = asyncio.run_coroutine_threadsafe(connect(user), sys_loop)
    result = future.result()
    if result == StatusType.ERROR:
        sys_loop.call_soon_threadsafe(sys_loop.stop)
        sys_thread.join()
        return

    # set up GUI
    qapp = QApplication(sys.argv)  
    gui = GUI(user, sys_loop)

    # start the backend thread and GUI main thread
    asyncio.run_coroutine_threadsafe(exec(user, qapp), sys_loop)
    gui.show()
    qapp.exec()

    # if the user closes the GUI, disconnects from the main server
    future = asyncio.run_coroutine_threadsafe(disconnect(user), sys_loop)
    _ = future.result()

    sys_loop.call_soon_threadsafe(sys_loop.stop)
    sys_thread.join()

