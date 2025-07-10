from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget, QLabel,
    QHBoxLayout, QVBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QMessageBox,
    QStyledItemDelegate
)
from PyQt5.QtGui import QIcon, QColor, QPen, QPixmap, QImage

import math
import asyncio
import numpy as np


class GUI(QMainWindow):
    """Handles the GUI of the voicechat system"""

    FRAMERATE = 15
    BUTTON_SIZE = 50

    def __init__(self, user, sys_loop):
        super().__init__()

        self.user = user # the user this GUI is showing for
        self.sys_loop = sys_loop # loop for backend server-client communication

        self.set_main()
        self.setup()


    def set_main(self):
        """Set up the GUI main loop"""
  
        self.main_thread = QThread() # thread for main loop
        self.main = Main(self)
        self.main.moveToThread(self.main_thread)

        self.image_thread = QThread() # thread for displaying participant data
        self.participant_delegate = ParticipantDelegate()
        self.participant_delegate.moveToThread(self.image_thread)

        self.timer = QTimer()
        self.timer.timeout.connect(self.main.run) # timer for main loop


    def show(self):
        """Show the GUI, and start the main loop"""
        self.main_thread.start()
        self.timer.start(1000 // GUI.FRAMERATE)
        super().show()


    def setup(self):
        """Set up the GUI"""

        self.setWindowTitle("Voicechat System")
        self.setGeometry(100, 100, 1080, 810)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)


        # Chatroom list interface
        chatroom_widget = QWidget()
        chatroom_widget.setFixedWidth(250)
        self.main_layout.addWidget(chatroom_widget)
        chatroom_layout = QVBoxLayout(chatroom_widget)

        chatroom_list_label = QLabel()
        chatroom_list_label.setText("Chatroom list")
        chatroom_layout.addWidget(chatroom_list_label)

        self.chatroom_list_widget = QListWidget()
        self.chatroom_list_widget.itemClicked.connect(self.join_chatroom)
        chatroom_layout.addWidget(self.chatroom_list_widget)

        create_chatroom_button = QPushButton("Create a new chatroom")
        create_chatroom_button.clicked.connect(self.create_chatroom)
        chatroom_layout.addWidget(create_chatroom_button)


        # Chatroom interface
        chatroom_widget = QWidget()
        chatroom_layout = QHBoxLayout(chatroom_widget)
        self.main_layout.addWidget(chatroom_widget)


        # Voicechatting interface
        voicechat_widget = QWidget()
        voicechat_layout = QVBoxLayout(voicechat_widget)
        chatroom_layout.addWidget(voicechat_widget)

        # Chatroom label
        self.chatroom_label = QLabel()
        self.chatroom_label.setStyleSheet("font-size: 12pt;")
        voicechat_layout.addWidget(self.chatroom_label)

        # Recording control
        self.recording_widget = QWidget()
        recording_layout = QHBoxLayout(self.recording_widget)
        self.recording_widget.setFixedHeight(80)

        self.recording_label = QLabel()
        recording_layout.addWidget(self.recording_label)

        self.recording_button = QPushButton()
        self.recording_button.clicked.connect(self.toggle_recording)
        self.recording_button.setFixedSize(3 * GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        recording_layout.addWidget(self.recording_button)
        
        self.update_recording_status(False)

        voicechat_layout.addWidget(self.recording_widget)


        # Participants data
        self.chat_widget = QTableWidget()
        self.chat_widget.horizontalHeader().setVisible(False)
        self.chat_widget.verticalHeader().setVisible(False)
        self.chat_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.chat_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_widget.setItemDelegate(self.participant_delegate)

        voicechat_layout.addWidget(self.chat_widget)


        # Control buttons
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)

        self.webcam_button = QPushButton()
        self.webcam_button.clicked.connect(self.toggle_webcam)
        self.webcam_button.setFixedSize(GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        self.update_webcam_button(False)
        control_layout.addWidget(self.webcam_button)

        self.filter_button = QPushButton()
        self.filter_button.clicked.connect(self.toggle_filter)
        self.filter_button.setFixedSize(GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        self.update_filter_button(False)
        control_layout.addWidget(self.filter_button)

        self.microphone_button = QPushButton()
        self.microphone_button.clicked.connect(self.toggle_microphone)
        self.microphone_button.setFixedSize(GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        self.update_microphone_button(False)
        control_layout.addWidget(self.microphone_button)

        self.speaker_button = QPushButton()
        self.speaker_button.clicked.connect(self.toggle_speaker)
        self.speaker_button.setFixedSize(GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        self.update_speaker_button(False)
        control_layout.addWidget(self.speaker_button)

        self.exit_button = QPushButton("Quit")
        self.exit_button.clicked.connect(self.quit_chatroom)
        self.exit_button.setToolTip("Quit chatroom")
        self.exit_button.setFixedSize(GUI.BUTTON_SIZE, GUI.BUTTON_SIZE)
        control_layout.addWidget(self.exit_button)

        voicechat_layout.addWidget(control_widget)


        # set participant list (withhold)
        participant_widget = QWidget()
        participant_widget.setFixedWidth(350)
        participant_layout = QVBoxLayout(participant_widget)
        # chatroom_layout.addWidget(participant_widget, alignment=Qt.AlignmentFlag.AlignRight)

        self.participant_label = QLabel()
        self.participant_label.setStyleSheet("font-size: 12pt;")
        participant_layout.addWidget(self.participant_label)

        self.participant_list_widget = QTableWidget()
        self.participant_list_widget.horizontalHeader().setVisible(False)
        self.participant_list_widget.verticalHeader().setVisible(False)
        self.participant_list_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.participant_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.participant_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.participant_list_widget.setColumnCount(1)
        self.participant_list_widget.setColumnWidth(0, self.participant_list_widget.geometry().width())

        participant_layout.addWidget(self.participant_list_widget)


        self.set_message_box()


    def set_message_box(self):
        """Set error message box"""

        self.create_chatroom_message_box = QMessageBox()
        self.create_chatroom_message_box.setIcon(QMessageBox.Warning)
        self.create_chatroom_message_box.setWindowTitle("Error")
        self.create_chatroom_message_box.setStandardButtons(QMessageBox.Ok)
        self.create_chatroom_message_box.setText(
            "Cannot join another chatroom while in a chatroom. " +
            "Please quit the current chatroom first."
        )
        self.create_chatroom_message_box.setFixedSize(400, 200)

        self.join_chatroom_message_box = QMessageBox()
        self.join_chatroom_message_box.setIcon(QMessageBox.Warning)
        self.join_chatroom_message_box.setWindowTitle("Error")
        self.join_chatroom_message_box.setStandardButtons(QMessageBox.Ok)
        self.join_chatroom_message_box.setText(
            "Cannot join another chatroom while in a chatroom. " +
            "Please quit the current chatroom first."
        )
        self.join_chatroom_message_box.setFixedSize(400, 200)


    @pyqtSlot(list)
    def update_chatroom_list(self, *args):
        """Update chatroom list"""
        chatroom_list = args[0]
        for cid in chatroom_list:
            self.chatroom_list_widget.addItem(f"Chatroom {cid}")

    
    @pyqtSlot(list)
    def update_participant_data(self, *args):
        """Update participant data in current chatroom"""
 
        participant_data = args[0]

        if (n_participants := len(participant_data)) == 0:
            self.chatroom_label.setText("Not in Chatroom")
            self.chat_widget.clearContents()
            self.chat_widget.setRowCount(0)
            self.chat_widget.setColumnCount(0)
            return


        # set chatroom label
        self.chatroom_label.setText(f"Chatroom {self.user.chatroom_ID}")

        # update voicechat data of each participant
        # show the participants in grids
        grid_size = math.ceil(n_participants ** .5)
        self.chat_widget.setRowCount(grid_size)
        self.chat_widget.setColumnCount(grid_size)

        for i in range(grid_size):
            self.chat_widget.setRowHeight(i, self.chat_widget.geometry().height() // grid_size)
            self.chat_widget.setColumnWidth(i, self.chat_widget.geometry().width() // grid_size)

        for i, participant in enumerate(participant_data):
            r = i // grid_size
            c = i % grid_size
            
            item_widget = QTableWidgetItem()

            # display a green border if microphone is unmuted
            if participant.microphone:
                item_widget.setData(Qt.UserRole, QPen(QColor("#32CD32"), 5))

            # display the webcam image if webcam is on, otherwise, show the participant name
            if participant.webcam and participant.image is not None:
                item_widget.setData(Qt.DisplayRole, participant.image)

            else:
                item_widget.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_widget.setText(f"Participant {participant.id}")

            self.chat_widget.setItem(r, c, item_widget)

    ### withhold
    @pyqtSlot(list)
    def update_participant_list(self, *args):
        """Update participant list in current chatroom"""

        participant_data = args[0]

        if (n_participants := len(participant_data)) == 0:
            self.participant_label.setText("")
            self.participant_list_widget.clear()
            self.participant_list_widget.setRowCount(0)
            return

        if n_participants == 1:
            self.participant_label.setText(f"Participant (1)")
        else:
            self.participant_label.setText(f"Participants ({n_participants})") 


        self.participant_list_widget.clear()
        self.participant_list_widget.setRowCount(n_participants)

        for i, participant in enumerate(participant_data):

            self.participant_list_widget.setRowHeight(i, 50)
            
            item_widget = QWidget()
            item_widget_layout = QHBoxLayout()
            item_widget.setLayout(item_widget_layout)           

            label = QLabel(f"Participant {participant.id}")
            item_widget_layout.addWidget(label)

            webcam_status = QLabel()
            if participant.webcam:
                webcam_status.setPixmap(QPixmap("util/camera.svg"))
            else:
                webcam_status.setPixmap(QPixmap("util/camera-off.svg"))
            webcam_status.setFixedSize(40, 40)
            item_widget_layout.addWidget(webcam_status, alignment=Qt.AlignmentFlag.AlignRight)

            microphone_status = QLabel()
            if participant.microphone:
                microphone_status.setPixmap(QPixmap("util/mic.svg"))
            else:
                microphone_status.setPixmap(QPixmap("util/mic-mute.svg"))
            microphone_status.setFixedSize(40, 40)
            item_widget_layout.addWidget(microphone_status, alignment=Qt.AlignmentFlag.AlignRight)
        
            speaker_status = QLabel()
            if participant.speaker:
                speaker_status.setPixmap(QPixmap("util/speaker.svg"))
            else:
                speaker_status.setPixmap(QPixmap("util/speaker-mute.svg"))
            speaker_status.setFixedSize(40, 40)
            item_widget_layout.addWidget(speaker_status, alignment=Qt.AlignmentFlag.AlignRight)

            self.participant_list_widget.setCellWidget(i, 0, item_widget)


    
    @pyqtSlot(bool)
    def update_recording_status(self, *args):
        """Update recording status in a chatroom"""      
        recording_status = args[0]
        if recording_status:
            self.recording_label.setText("Recording started")
            self.recording_button.setText("Stop recording")
            self.recording_button.setIcon(QIcon("util/stop.svg"))
        
        else:
            self.recording_label.setText("Recording stopped")
            self.recording_button.setText("Start recording")  
            self.recording_button.setIcon(QIcon("util/play.svg"))         


    def update_microphone_button(self, on: bool):
        if on:
            self.microphone_button.setIcon(QIcon("util/mic-mute.svg"))
            self.microphone_button.setToolTip("Mute microphone")
        else:
            self.microphone_button.setIcon(QIcon("util/mic.svg"))
            self.microphone_button.setToolTip("Unmute microphone")
       

    def update_speaker_button(self, on: bool):
        if on:
            self.speaker_button.setIcon(QIcon("util/speaker-mute.svg"))
            self.speaker_button.setToolTip("Mute speaker")
        else:
            self.speaker_button.setIcon(QIcon("util/speaker.svg"))
            self.speaker_button.setToolTip("Unmute speaker")     


    def update_webcam_button(self, on: bool):
        if on:
            self.webcam_button.setIcon(QIcon("util/camera-off.svg"))
            self.webcam_button.setToolTip("Turn off webcam")
        else:
            self.webcam_button.setIcon(QIcon("util/camera.svg"))
            self.webcam_button.setToolTip("Turn on webcam")  


    def update_filter_button(self, on: bool):
        if on:
            self.filter_button.setIcon(QIcon("util/mask-off.png"))
            self.filter_button.setToolTip("Turn off filter")
        else:
            self.filter_button.setIcon(QIcon("util/mask.png"))
            self.filter_button.setToolTip("Turn on filter")  


    def create_chatroom(self, *args):
        """Create a chatroom"""
        if self.user.connected_chatroom:
            self.create_chatroom_message_box.exec()
            return
        
        asyncio.run_coroutine_threadsafe(self.user.create_chatroom(), self.sys_loop)
        
        self.update_microphone_button(True)
        self.update_speaker_button(True)


    def join_chatroom(self, *args):
        """Join a chatroom"""
        if self.user.connected_chatroom:
            self.join_chatroom_message_box.exec()
            return
        
        chatroom_ID = args[0].text().split()[-1]
        chatroom_ID = int(chatroom_ID)
        asyncio.run_coroutine_threadsafe(self.user.join_chatroom(chatroom_ID), self.sys_loop)
        
        self.update_microphone_button(True)
        self.update_speaker_button(True)


    def quit_chatroom(self, *args):
        """Quit the chatroom"""
        if not self.user.connected_chatroom: return
        asyncio.run_coroutine_threadsafe(self.user.quit_chatroom(), self.sys_loop)
        
        self.update_microphone_button(False)
        self.update_speaker_button(False)
        self.update_webcam_button(False)


    def toggle_microphone(self, *args):
        """Toggle mute and unmute of microphone"""
        if not self.user.connected_chatroom: return
        result = asyncio.run_coroutine_threadsafe(self.user.toggle_microphone(), self.sys_loop)
        self.update_microphone_button(result.result())


    def toggle_speaker(self, *args):
        """Toggle mute and unmute of speakers"""
        if not self.user.connected_chatroom: return
        result = asyncio.run_coroutine_threadsafe(self.user.toggle_speaker(), self.sys_loop)
        self.update_speaker_button(result.result())


    def toggle_webcam(self, *args):
        """Toggle on and off of webcam"""
        if not self.user.connected_chatroom: return
        result = asyncio.run_coroutine_threadsafe(self.user.toggle_webcam(), self.sys_loop)
        self.update_webcam_button(result.result())


    def toggle_filter(self, *args):
        """Toggle webcam filter on and off"""
        if not self.user.connected_chatroom or not self.user.webcam: return
        result = asyncio.run_coroutine_threadsafe(self.user.toggle_filter(), self.sys_loop)
        self.update_filter_button(result.result())


    def toggle_recording(self, *args):
        """Toggle recording"""
        if not self.user.connected_chatroom: return
        asyncio.run_coroutine_threadsafe(self.user.toggle_recording(), self.sys_loop)



class Main(QObject):
    """Handles GUI main loop functions that retrieves data from server"""

    UPDATE_CHATROOM = pyqtSignal(list)
    UPDATE_PARTICIPANT_DATA = pyqtSignal(list)
    UPDATE_PARTICIPANT_LIST = pyqtSignal(list)
    UPDATE_RECORDING_STATUS = pyqtSignal(bool)

    def __init__(self, gui: GUI):
        super().__init__()
        self.gui = gui
        self.set_signal()
        
        self.chatroom_list = []
        self.participant_list = []
        self.recording_status = False


    def set_signal(self):
        self.UPDATE_CHATROOM.connect(self.gui.update_chatroom_list)
        self.UPDATE_PARTICIPANT_DATA.connect(self.gui.update_participant_data)
        self.UPDATE_PARTICIPANT_LIST.connect(self.gui.update_participant_list) ### withhold
        self.UPDATE_RECORDING_STATUS.connect(self.gui.update_recording_status)


    @pyqtSlot()
    def run(self):
        """Retrieve data from server, and update the GUI if changed"""

        # get chatroom list from system server
        result = asyncio.run_coroutine_threadsafe(
            self.gui.user.request_chatroom_list(), self.gui.sys_loop
        )
        # only update if changed
        chatroom_list = result.result()
        if chatroom_list is not None and chatroom_list != self.chatroom_list:     
            # only add newly-created chatrooms to list
            new_list = list(set(chatroom_list) - set(self.chatroom_list))
            if len(new_list) > 0:
                self.UPDATE_CHATROOM.emit(new_list)
            self.chatroom_list = chatroom_list


        # get participant data from the chatroom server
        result = asyncio.run_coroutine_threadsafe(
            self.gui.user.request_participant_data(), self.gui.sys_loop
        )
        # only update if changed
        participant_data = result.result()

        if participant_data is not None:
            # with webcam image
            self.UPDATE_PARTICIPANT_DATA.emit(participant_data)

            ### withhold
            # list and status of participant
            # for p in participant_data: p.image = None
            # if not np.all(participant_data == self.participant_data): 
            #     self.participant_data = participant_data
            #     self.UPDATE_PARTICIPANT_LIST.emit(participant_data)


        # get recording status from chatroom server
        result = asyncio.run_coroutine_threadsafe(
            self.gui.user.request_recording_status(), self.gui.sys_loop
        )
        # only update if changed
        recording_status = result.result()
        if recording_status != self.recording_status:
            self.recording_status = recording_status
            self.UPDATE_RECORDING_STATUS.emit(recording_status)



class ParticipantDelegate(QStyledItemDelegate):
    """Draw participant data"""

    def __init__(self):
        super().__init__()


    def paint(self, painter, option, index):

        super().paint(painter, option, index)   
    
        painter.save()

        # draw a border if the participant is not muted
        if (data := index.data(Qt.UserRole)) is not None:
            painter.setPen(data)
            painter.drawRect(option.rect.adjusted(1, 1, -1, -1))

        # show the webcam image if the participant enabled the camera
        if (data := index.data(Qt.DisplayRole)) is not None and isinstance(data, np.ndarray):
            h, w, c = data.shape
            image = QImage(data, w, h, w*c, QImage.Format_RGB888)
            # image = image.scaled(option.rect.adjusted(6, 6, -6, -6).size(), Qt.KeepAspectRatio)
            painter.drawImage(option.rect.adjusted(6, 6, -6, -6), image)

        painter.restore()

