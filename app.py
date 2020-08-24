# local
import gui
import util
# external
from PIL import Image
import json
import os
import random
import requests
import shutil
import sys
import threading
import time


def clean_cache():
    cache_image_filepath = ImageboardQuizApplication.CACHE_FOLDER_WIN \
        if sys.platform == 'win32' else ImageboardQuizApplication.CACHE_FOLDER_UNIX
    if os.path.exists(cache_image_filepath):
        shutil.rmtree(cache_image_filepath)


class ImageboardQuizApplication:
    API_URL = "https://a.4cdn.org/"
    IMAGE_URL = "https://is2.4chan.org/"
    CACHE_FOLDER_UNIX = "resource/cache/"
    CACHE_FOLDER_WIN = "resource\\cache\\"

    def __init__(self):
        self.interface = None
        self.current_game = None
        self.options = {"sfw": False, "round_length": 20}

    def initialize_interface(self, interface_type):
        if interface_type == "gui":
            self.initialize_gui()
        elif interface_type == "cli":
            raise NotImplementedError("CLI mode is not yet implemented")
        else:
            raise ValueError("Unknown interface type {}".format(interface_type))

    def initialize_gui(self):
        self.interface = gui.MainWindow(self)
        self.interface.mainloop()

    def start_game(self):
        board_list = self.download_board_list()
        self.update_board_dropdown(board_list)
        self.current_game = Game(self, board_list)
        self.current_game.start_round()

    def download_board_list(self):
        suffix = "boards.json"

        self.status_message_to_gui("Downloading board list...")

        request = requests.get("{}{}".format(ImageboardQuizApplication.API_URL, suffix))

        boards = []

        if request.status_code == 200:
            boards_dict = json.loads(request.text)
            if "boards" in boards_dict:
                for board in boards_dict["boards"]:
                    if "board" in board and board["board"] != "f":
                        if self.options["sfw"] and bool(board["ws_board"]) is False:
                            continue
                        else:
                            boards.append((board["board"], bool(board["ws_board"]), board["title"]))
            time.sleep(1.2)

        self.status_message_to_gui()

        return boards

    def download_thread_list(self, board):
        suffix = "{}/catalog.json".format(board[0])
        request_url = "{}{}".format(ImageboardQuizApplication.API_URL, suffix)
        catalog_dict = None

        self.status_message_to_gui("Downloading catalog...")

        request = requests.get(request_url)

        if request.status_code == 200:
            catalog_dict = json.loads(request.text)
            time.sleep(1.2)
        else:
            print("Could not download catalog; status code {}".format(request.status_code))

        self.status_message_to_gui()

        return catalog_dict

    def update_game_frame(self, thread):
        self.interface.update_game_frame(thread)

    def update_board_dropdown(self, boards):
        self.interface.update_board_dropdown(boards)

    def enable_interactive_frame(self):
        util.logging_message(self, "Enabling controls")
        self.interface.enable_interactive_frame()

    def download_image(self, board, name, extension):
        max_size = 300, 300

        suffix = "{}/{}".format(board, name)
        cache_image_filepath = "{}{}".format(
            ImageboardQuizApplication.CACHE_FOLDER_WIN if sys.platform == 'win32'
            else ImageboardQuizApplication.CACHE_FOLDER_UNIX,
            name)
        request_url = "{}{}".format(ImageboardQuizApplication.IMAGE_URL, suffix)
        print(request_url)

        if extension != ".png" and extension != ".jpg" and extension != ".gif":
            return None

        self.status_message_to_gui("Downloading OP image...")

        request = requests.get(request_url, stream=True)

        if request.status_code == 200:
            os.makedirs(os.path.dirname(cache_image_filepath), exist_ok=True)
            with open(cache_image_filepath, 'wb') as file:
                request.raw.decode_content = True
                shutil.copyfileobj(request.raw, file)
        time.sleep(1.2)

        image = Image.open(cache_image_filepath, mode='r')
        if extension == ".gif":
            image = image.seek(0)

        image.thumbnail(max_size, Image.ANTIALIAS)

        self.status_message_to_gui()

        return image

    def status_message_to_gui(self, status=None):
        if self.interface is not None:
            self.interface.update_status(status)

    def clean_up(self):
        if self.current_game is not None:
            self.current_game.end_current_round()
        clean_cache()

    def set_sfw_only(self, value):
        # print("Changing the value to {}".format(value.get()))
        self.options["sfw"] = value.get()


class Timer(threading.Thread):
    def __init__(self, start_time, gui, game_round):
        threading.Thread.__init__(self)
        self.time = start_time * 1.
        self.stop_timer = threading.Event()
        self.gui = gui
        self.round = game_round

    def run(self):
        self.count_down()

    def count_down(self):
        while True:
            time.sleep(0.1)
            self.time = self.time - 0.1
            self.update_gui_timer()
            if self.stop_timer.is_set():
                # print("Timer stopped!")
                break
            if self.time < 0.1:
                self.interrupt_round()
                break

    def update_gui_timer(self):
        if self.gui is not None and not self.stop_timer.is_set():
            self.gui.update_timer(self.time)

    def set_stop_flag(self):
        self.stop_timer.set()
        # print("Set stop flag")

    def interrupt_round(self):
        self.round.interrupt()


class Game:
    def __init__(self, application, board_list):
        self.application = application
        self.boards = board_list

        self.history = []
        self.current_round = None

    def start_round(self):
        board = self.get_random_board()
        thread = self.get_random_thread(board)
        self.current_round = Round(self, thread, 20.)
        self.update_round(thread)

    def end_current_round(self):
        if self.current_round is not None:
            self.history.append(self.current_round)
            self.current_round.end()
            self.current_round = None

    def get_random_board(self):
        return random.choice(self.boards)

    def enable_interactive_frame(self):
        print("{}: Enabling controls".format(self.__class__.__name__))
        self.application.enable_interactive_frame()

    def update_round(self, thread):
        self.application.update_game_frame(thread)

    def submit_answer(self, answer):
        if self.current_round is not None:
            self.current_round.compare_answer(answer)

    def get_random_thread(self, board):
        catalog = self.application.download_thread_list(board)
        random_page_dict = random.choice(catalog)
        random_thread_dict = None
        if "threads" in random_page_dict:
            random_thread_dict = random.choice(random_page_dict["threads"])

        image = None
        if "tim" in random_thread_dict and random_thread_dict["tim"] is not None:
            image_filename = "{}{}".format(random_thread_dict["tim"], random_thread_dict["ext"])
            image = self.application.download_image(board[0], image_filename, random_thread_dict["ext"])

        thread = Thread(
            board=board[0],
            timestamp=random_thread_dict["now"],
            user=random_thread_dict["name"],
            tripcode=random_thread_dict["trip"] if "trip" in random_thread_dict else None,
            comment=random_thread_dict["com"] if "com" in random_thread_dict else None,
            subject=random_thread_dict["sub"] if "sub" in random_thread_dict else None,
            image=image
        )

        self.history.append(thread)

        return thread


class Round:
    def __init__(self, game, thread, time_limit):
        self.game = game
        self.thread = thread
        self.time_limit = time_limit
        self.timer = None

        self.start_round()

    def start_round(self):
        self.game.enable_interactive_frame()
        self.timer = Timer(self.time_limit, self.game.application.interface, self)
        self.timer.start()

    def end(self):
        if self.timer is not None:
            self.timer.set_stop_flag()

    def interrupt(self):
        self.end()

    def compare_answer(self, answer):
        self.end()
        print(self.thread.board)
        print(answer)


class Thread:
    def __init__(self, board, timestamp, user=None, tripcode=None, comment=None, subject=None, image=None):
        self.board = board
        self.timestamp = timestamp
        self.user = user
        self.tripcode = tripcode
        self.comment = comment
        self.subject = subject
        self.image = image

    def __str__(self):
        return "/{}/; user: {}, subject: {}, timestamp: {}".format(self.board, self.user, self.subject, self.timestamp)


if __name__ == "__main__":
    app = ImageboardQuizApplication()
    app.initialize_interface("gui")
