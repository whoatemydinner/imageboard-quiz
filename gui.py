# local
import util
# external
from PIL import ImageTk
import time
import tkinter as tk
import tkinter.scrolledtext as tkscrolled
import tkinter.ttk as ttk


class MainWindow(tk.Tk):
    def __init__(self, application):
        tk.Tk.__init__(self)
        self.application = application
        self.status_text = tk.StringVar()
        self.status_text.set("Ready")

        self.sfw_var = tk.BooleanVar()
        self.sfw_var.set(self.application.options["sfw"])
        self.sfw_var.trace_add("write", lambda x, y, z: self.application.set_sfw_only(self.sfw_var))

        self.game_frame = DisplayFrame(self, bg="#eef2ff")
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
        self.options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.options_menu.add_checkbutton(label="SFW boards only", onvalue=1, offvalue=0, variable=self.sfw_var)
        self.menu_bar.add_cascade(label="Options", menu=self.options_menu)

        self.config(menu=self.menu_bar)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_status(self, message=None):
        self.status_text.set(message if message is not None else "Ready")
        self.status_bar.update()

    def update_game_frame(self, thread):
        self.game_frame.display_data(thread)

    def update_board_dropdown(self, boards):
        util.logging_message(self, "Updating board dropdown")
        formatted_board_dict = {}
        for board in boards:
            board_formatted = ("/{}/ - {}".format(board[0], board[2]))
            formatted_board_dict[board_formatted] = board[0]
        self.interactive_frame.update_board_dropdown(formatted_board_dict)

    def enable_interactive_frame(self):
        self.interactive_frame.enable()

    def update_timer(self, timer_time):
        self.interactive_frame.update_timer(timer_time)

    def on_closing(self):
        self.application.clean_up()
        time.sleep(0.5)
        self.destroy()

    def submit_answer(self, answer):
        self.application.current_game.submit(answer)

class InteractiveFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.board_dict = {}
        self.choice = tk.StringVar()

        self.timer_label = tk.Label(self, bg=self["background"], text="Time left:")
        self.timer_label.grid(row=0, column=0, sticky=tk.W, padx=10)
        self.timer = tk.Label(self, bg=self["background"])
        self.timer.grid(row=0, column=1, sticky=tk.W, padx=10)
        self.grid_columnconfigure(1, weight=1)

        self.boards_dropdown = ttk.Combobox(self, values=[], state=tk.DISABLED, textvariable=self.choice)
        self.boards_dropdown.grid(row=0, column=2, sticky=tk.E, padx=10)
        self.accept_button = tk.Button(self, text="Choose board", state=tk.DISABLED, command=self.submit)
        self.accept_button.grid(row=0, column=3, sticky=tk.E, padx=10)

    def update_board_dropdown(self, formatted_boards):
        self.board_dict = formatted_boards
        self.boards_dropdown["values"] = list(formatted_boards.keys())
        self.update()

    def disable(self):
        self.boards_dropdown["state"] = tk.DISABLED
        self.accept_button["state"] = tk.DISABLED
        self.update()

    def enable(self):
        self.boards_dropdown["state"] = tk.NORMAL
        self.accept_button["state"] = tk.NORMAL
        self.update()

    def update_timer(self, timer_time):
        self.timer["text"] = "{:.2f}s".format(timer_time)

    def submit(self):
        self.master.submit(self.board_dict[self.choice.get()])


class DisplayFrame(tk.Frame):
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

        self.comment_box = tkscrolled.ScrolledText(self, height=15, bg=self["background"], relief=tk.FLAT,
                                             font=('sans-serif', 10), fg="#0d0d07")
        self.comment_box.grid(row=1, column=1, columnspan=4)

    def reset(self):
        self.update_image()
        self.subject_box["text"] = ""
        self.user_box["text"] = "Anonymous"
        self.trip_box["text"] = ""
        self.timestamp_box["text"] = "01/01/70(Thu)21:37:00"
        self.comment_box.delete("1.0", tk.END)
        self.update()

    def display_data(self, thread):
        self.reset()
        if thread.subject is not None:
            self.subject_box["text"] = thread.subject
        if thread.user is not None:
            self.user_box["text"] = thread.user
        if thread.tripcode is not None:
            self.trip_box["text"] = thread.tripcode
        self.timestamp_box["text"] = thread.timestamp
        if thread.comment is not None:
            self.comment_box.insert("1.0", util.format_comment(thread.comment))
        self.update_image(image=thread.image)
        self.update()

    def update_image(self, image=None):
        tk_image = ImageTk.PhotoImage(image) if image is not None else ImageTk.PhotoImage(file="resource/logo.png")
        self.image_canvas.gfx = tk_image
        self.image_canvas.create_image(0, 0, image=self.image_canvas.gfx, anchor="nw")
        self.update()


if __name__ == "__main__":
    pass
