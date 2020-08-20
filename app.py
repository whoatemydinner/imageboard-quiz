from PIL import Image, ImageTk
from tkinter import ttk
import json
import os
import sys
import tkinter as tk
import tkinter.scrolledtext as tkst
import time
import random
import requests
import shutil
import threading
import re


def format_comment(text: str):
    comment = re.sub(r"<a.*?>", "", text)
    comment = re.sub(r"<br>", "\n", comment)
    comment = re.sub(r"<wbr>", "", comment)
    comment = re.sub(r"<span.*?>", "", comment)
    comment = re.sub(r"</.*?>", "", comment)
    comment = comment.replace("&gt;", ">")
    comment = comment.replace("&#039;", "'")
    comment = comment.replace("&quot;", "\"")
    return comment


class ImageboardQuizApplication:
    API_URL = "https://a.4cdn.org/"
    IMAGE_URL = "https://is2.4chan.org/"
    CACHE_FOLDER_UNIX = "resource/cache/"
    CACHE_FOLDER_WIN = "resource\\cache\\"

    def __init__(self):
        self.gui = None
        self.game = None

    def initialize_gui(self):
        self.gui = MainWindow(self)
        self.gui.mainloop()

    def start_game(self):
        board_list = self.download_board_list()
        self.update_board_dropdown(board_list)
        self.game = Game(self, board_list)
        self.game.start_level()

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
        self.gui.update_game_frame(thread)

    def update_board_dropdown(self, boards):
        self.gui.update_board_dropdown(boards)

    def enable_interactive_frame(self):
        self.gui.enable_interactive_frame()

    def download_image(self, board, name, extension):
        max_size = 300, 300

        suffix = "{}/{}".format(board, name)
        cache_image_filepath = "{}{}".format(
            ImageboardQuizApplication.CACHE_FOLDER_WIN if sys.platform == 'win32'
            else ImageboardQuizApplication.CACHE_FOLDER_UNIX,
            name)
        request_url = "{}{}".format(ImageboardQuizApplication.IMAGE_URL, suffix)
        print(request_url)

        if extension != ".png" and extension != ".jpg":
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
        image.thumbnail(max_size, Image.ANTIALIAS)

        self.status_message_to_gui()

        return image

    def status_message_to_gui(self, status=None):
        if self.gui is not None:
            self.gui.change_status_bar(status)


class Timer(threading.Thread):
    def __init__(self, start_time):
        threading.Thread.__init__(self)
        self.time = start_time

    def run(self):
        while True:
            self.count_down()

    def count_down(self):
        print("Time left: {}".format(self.time))
        time.sleep(1)
        self.time = self.time - 1


class Game:
    def __init__(self, application, board_list):
        self.application = application
        self.boards = board_list

        self.history = []

        self.timer = None

    def start_level(self):
        # self.timer = Timer(10)
        # self.timer.start()
        self.application.enable_interactive_frame()
        board = self.get_random_board()
        print(board)
        thread = self.get_random_thread(board)
        self.application.update_game_frame(thread)

    def get_random_board(self):
        return random.choice(self.boards)

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


class MainWindow(tk.Tk):
    def __init__(self, application):
        tk.Tk.__init__(self)
        self.application = application
        self.status_text = tk.StringVar()
        self.status_text.set("Ready")

        self.game_frame = ThreadFrame(self, bg="#eef2ff")
        self.game_frame.grid(row=0, column=0)

        self.interactive_frame = InteractiveFrame(self)
        self.interactive_frame.grid(row=1, column=0, sticky="SWE")

        self.status_bar = tk.Label(self, textvar=self.status_text, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, sticky="SW")

        self.menu_bar = tk.Menu(self)
        self.game_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.game_menu.add_command(label="Begin", command=self.application.start_game)
        self.game_menu.add_separator()
        self.game_menu.add_command(label="Exit", command=self.quit)
        self.menu_bar.add_cascade(label="Game", menu=self.game_menu)

        self.config(menu=self.menu_bar)

    def change_status_bar(self, message=None):
        self.status_text.set(message if message is not None else "Ready")
        self.status_bar.update()

    def update_game_frame(self, thread):
        self.game_frame.update_thread_data(thread)

    def update_board_dropdown(self, boards):
        print("updating board dropdown")
        formatted_board_list = []
        for board in boards:
            formatted_board_list.append("/{}/ - {}".format(board[0], board[2]))
        self.interactive_frame.update_board_list(formatted_board_list)

    def enable_interactive_frame(self):
        self.interactive_frame.enable_elements()


class InteractiveFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.choice = tk.StringVar()

        self.timer_label = tk.Label(self, bg=self["background"], text="Time left:")
        self.timer_label.grid(row=0, column=0, sticky=tk.W, padx=10)
        self.timer = tk.Label(self, bg=self["background"])
        self.timer.grid(row=0, column=1, sticky=tk.W, padx=10)
        self.grid_columnconfigure(1, weight=1)

        self.boards_dropdown = ttk.Combobox(self, values=[], state=tk.DISABLED)
        self.boards_dropdown.grid(row=0, column=2, sticky=tk.E, padx=10)
        self.accept_button = tk.Button(self, text="Choose board", state=tk.DISABLED)
        self.accept_button.grid(row=0, column=3, sticky=tk.E, padx=10)

    def update_board_list(self, boards):
        self.boards_dropdown["values"] = boards
        self.update()

    def disable_elements(self):
        self.boards_dropdown["state"] = tk.DISABLED
        self.accept_button["state"] = tk.DISABLED
        self.update()

    def enable_elements(self):
        self.boards_dropdown["state"] = tk.NORMAL
        self.accept_button["state"] = tk.NORMAL
        self.update()


class ThreadFrame(tk.Frame):
    def __init__(self, master, **params):
        super().__init__(master, **params)

        self.image_canvas = tk.Canvas(self, width=300, height=300, bg=self["background"])
        self.image_canvas.grid(row=0, column=0, rowspan=2)
        self.update_image()

        self.subject_box = tk.Label(self, bg=self["background"], fg="#0f0c5d", font=('sans-serif', 10, 'bold'))
        self.subject_box.grid(row=0, column=1, sticky=tk.W)
        self.user_box = tk.Label(self, text="Anonymous", bg=self["background"], fg="#117743",
                                 font=('sans-serif', 10,  'bold'))
        self.user_box.grid(row=0, column=2, sticky=tk.W)
        self.trip_box = tk.Label(self, bg=self["background"])
        self.user_box.grid(row=0, column=3, sticky=tk.W)
        self.timestamp_box = tk.Label(self, text="01/01/70(Thu)21:37:00", bg=self["background"], fg="#0d0d07")
        self.timestamp_box.grid(row=0, column=4, sticky=tk.W)
        self.grid_columnconfigure(4, weight=1)

        self.comment_box = tkst.ScrolledText(self, height=15, bg=self["background"], relief=tk.FLAT,
                                             font=('sans-serif', 10), fg="#0d0d07")
        self.comment_box.grid(row=1, column=1, columnspan=4)

    def update_thread_data(self, thread):
        print(str(thread))
        if thread.subject is not None:
            self.subject_box["text"] = thread.subject
        else:
            self.subject_box["text"] = ""
        if thread.user is not None:
            self.user_box["text"] = thread.user
        else:
            self.user_box["text"] = "Anonymous"
        if thread.tripcode is not None:
            self.trip_box["text"] = thread.tripcode
        else:
            self.trip_box["text"] = ""
        self.timestamp_box["text"] = thread.timestamp

        self.comment_box.delete("1.0", tk.END)
        if thread.comment is not None:
            self.comment_box.insert("1.0", format_comment(thread.comment))

        self.update_image(image=thread.image)
        self.update()

    def update_image(self, image=None, extension=None):
        tk_image = ImageTk.PhotoImage(image) if image is not None else ImageTk.PhotoImage(file="resource/logo.png")
        self.image_canvas.gfx = tk_image
        self.image_canvas.create_image(0, 0, image=self.image_canvas.gfx, anchor="nw")
        self.update()


if __name__ == "__main__":
    app = ImageboardQuizApplication()
    app.initialize_gui()
