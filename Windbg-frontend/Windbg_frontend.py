""" Made by Cpt-Dingus
Version 1.0.1 - 26/06/2023 """

import os
import subprocess
import sys
import tempfile
import threading
import zipfile
from queue import Empty, Queue
from tkinter import (
    BOTH,
    BOTTOM,
    DISABLED,
    END,
    LEFT,
    NORMAL,
    TOP,
    BooleanVar,
    Text,
    Tk,
    X,
    filedialog,
)
from tkinter.ttk import Button, Checkbutton, Frame, Notebook, Style


def push_message(window: Text, message: str):
    """
    Adds a message to the main info window.

    Args:
        - (tkinter.Text) - The window to append the message to
        - (str) message - The message to append
    """
    # Makes the window read only after it's done so you don't go changing
    # shit like the bloody rascal you are
    window.configure(state=NORMAL)
    window.insert(END, message)
    window.see(END)
    window.configure(state=DISABLED)


def get_input(prefix: str) -> str:
    """
    Gets the input from the respective queue

    Args:
      - (str) prefix - Prefix of the queue

    Returns:
      - (str) - The first entry of the queue if it isn't empty, otherwise returns None
    """
    input_queue = globals()[f"{prefix}_in"]
    try:
        return input_queue.get(block=False)
    except Empty:
        return None


def enqueue_output(stdout: subprocess.STDOUT, output: Queue):
    """
    -RAN AS A THREAD-
    Gets the output of a command without locking a thread

    Args:
        - (subprocess.STDOUT) stdout - The stdout to read
        - (queue.Queue) output - The queue to add the lines to
    """
    for line in iter(stdout.readline, b""):
        output.put(line)


def execute_command(process: subprocess.Popen, output: Queue, prefix: str):
    """
    -RAN AS A THREAD-
    Target of main threads, handles the stdio of a program

    Args:
        - (subprocess.Popen) process - The process to handle stdio of
        - (queue.Queue) output - The queue containing the output
        - (str) prefix - The variable prefix
    """
    output_window = globals()[f"{prefix}_window"]
    while THREAD_EXECUTE:
        # Gets any input made for this thread
        ind = get_input(prefix)
        if ind is not None:
            # Pushes it to the stdin
            process.stdin.write((ind + "\n").encode())
            process.stdin.flush()

        # Reads output lines without locking the thread
        try:
            line = output.get(timeout=1)
        except Empty:  # No output to write
            pass
        else:
            # CDB has stopped
            if "NatVis script unloaded from".encode() in line:
                push_message(output_window, "---Process has exited---")
                globals()[f"{prefix}_command"].configure(state=DISABLED)

                break  # Stops the thread

            # Excludes natvis bullshit
            if not "NatVis script".encode() in line:
                # Writes the output to the window
                push_message(output_window, line)


def get_files(file_path: str) -> dict:
    """
    Gets the files from a file path

    Args:
        - (str) file_path - The file path to get the files from
    """
    # Handling for zip files
    if file_path.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as unzipped_path:
            # Creates the temp dir
            tmpdir_path = tempfile.mkdtemp()

            for dump in unzipped_path.infolist():
                # Skips any files that are higher than the size limit or are non-dump files
                if (
                    not dump.filename.endswith(".dmp")
                    or dump.file_size > 1024 * 1024 * 100
                ):
                    continue

                # Makes a temp path for the dump file
                dump_path = os.path.join(tmpdir_path, f"{os.urandom(24).hex()}.dmp")

                # Writes to the temp directory
                with unzipped_path.open(dump, "r") as file, open(
                    dump_path, "wb+"
                ) as dest_file:
                    dest_file.write(file.read())

                # Gets the name of the dump file, replaces - with _ so it can be used as a prefix
                name = "".join(dump.filename.split("/")[-1]).replace("-", "_")

                # dump: path-to-dump
                files[name] = dump_path

    # Handling for dump files
    elif file_path.endswith(".dmp"):
        # Makes sure the size isn't over 100 MB
        if os.stat(file_path).st_size > 1024 * 1024 * 100:
            push_message(main_info, "Dump file exceeds maximum size (100 MB)\n")
            return None

        # Creates the temp dir
        tmpdir_path = tempfile.mkdtemp()
        dump_path = os.path.join(tmpdir_path, f"{os.urandom(24).hex()}.dmp")

        # Writes file to temp directory
        with open(file_path, "rb") as src_file, open(dump_path, "wb+") as dest_file:
            dest_file.write(src_file.read())

        # Gets the name of the dump file, replaces - with _ so it can be used as a prefix
        name = "".join(file_path.split("/")[-1]).replace("-", "_")

        # dump: path-to-dump
        files[name] = dump_path

    # Handling for folders
    else:
        # Makes sure no file got selected
        if "." in file_path:
            return None

        for file in os.listdir(file_path):
            if not file.endswith(".dmp"):
                continue
            # Creates the temp dir
            tmpdir_path = tempfile.mkdtemp()
            dump_path = os.path.join(tmpdir_path, f"{os.urandom(24).hex()}.dmp")

            # Writes file to temp directory
            with open(f"{file_path}\\{file}", "rb") as src_file, open(
                dump_path, "wb+"
            ) as dest_file:
                dest_file.write(src_file.read())

            # Makes sure the dictionary key doesn't contain - (an invalid character)
            name = file.replace("-", "_")

            # dump: path-to-dump
            files[name] = dump_path

    if files:
        return files

    # No files were succesfully parsed
    return None


def load_command():
    """
    Loads the files, starts their cdb threads
    """
    # Creates the tabs for all files
    file_path = file_path_box.get("1.0", END).strip()

    # Stops execution if the file path is invalid or doesn't exist
    if not file_path or not os.path.exists(file_path) and not os.path.isfile(file_path):
        return

    push_message(main_info, "Getting files...\n")

    # This updates the file dir globally
    get_files(file_path)
    if not files:
        return

    push_message(main_info, "Retrieved file list, defining tabs...\n")

    # Makes sure you can't modify the path afterwards
    select_button.configure(state=DISABLED)
    folder_select_button.configure(state=DISABLED)
    file_path_box.configure(state=DISABLED)

    # Creates tabs, puts everything in them
    for file in files:
        # Prefix used for variables
        prefix = file[:-4]

        # Creates tab and adds it to the tabControl
        globals()[f"{prefix}"] = Frame(tabControl)
        tab = globals()[f"{prefix}"]
        tabControl.add(tab, text=f"{file}")

        # Theme handling
        bg_theme = "#2d2d2d"
        fg_theme = "white"
        # Light mode handling
        if jim_mode.get():
            bg_theme = "white"
            fg_theme = "black"

        # Creates the main debugging window
        globals()[f"{prefix}_window"] = Text(
            tab, height=20, width=70, background=bg_theme, foreground=fg_theme
        )
        globals()[f"{prefix}_window"].pack(side=TOP, fill=BOTH, expand=True)

        # Creates the command box
        globals()[f"{prefix}_command"] = Text(
            tab, height=1, background=bg_theme, foreground=fg_theme
        )
        globals()[f"{prefix}_command"].pack(side=BOTTOM, fill=BOTH, padx=150, pady=40)
        # Binds entering to executing the command
        globals()[f"{prefix}_command"].bind(
            "<Return>", lambda x, prefix=prefix: run_command(x, prefix=prefix)
        )

    push_message(main_info, "Files loaded! Starting cdb threads...\n")

    # Starts thread for every file
    for file in files:
        # Prefix used for variables
        prefix = file[:-4]

        # Run the command and redirect its input and output
        command = f'{CDB_PATH} -z "{files[file]}"'
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Creates an output queue so the thread doesn't lock
        globals()[f"{prefix}_out"] = Queue()
        out_queue = globals()[f"{prefix}_out"]
        globals()[f"{prefix}_out_thread"] = threading.Thread(
            target=enqueue_output, args=(process.stdout, out_queue)
        )
        globals()[f"{prefix}_out_thread"].start()

        # Creates input queue so the thread can accept more than one line of input
        globals()[f"{prefix}_in"] = Queue()

        # Create a thread to execute the command loop
        globals()[f"{prefix}_thread"] = threading.Thread(
            target=execute_command, args=(process, out_queue, prefix)
        )
        globals()[f"{prefix}_thread"].start()

    push_message(main_info, "All cdb threads successfully started!\n")
    load_button.configure(state=DISABLED)

    run_default_button.configure(state=NORMAL)

    def run_command(_, prefix: str):
        """
        Pushes a command to the according stdin.

        Args:
            - (str) _ - The event, not used but passed to the func
            - (str) prefix - The prefix to use for variables
        """
        # Gets the command from the command box
        command = globals()[f"{prefix}_command"].get("1.0", END).strip()
        globals()[f"{prefix}_command"].delete(1.0, END)

        # Adds it to the command queue
        globals()[f"{prefix}_in"].put(command)


def run_default_commands():
    """
    Runs `k` and `!analyze` on all threads.
    """
    # Disables the start button so you don't go pressing it a kjghillion times
    run_default_button.configure(state="disabled")

    # Executed for every file
    for file in files:
        prefix = file[:-4]
        # Pushes `k` and `!!analyze` to the files' respective queues.
        globals()[f"{prefix}_in"].put("k")
        globals()[f"{prefix}_in"].put("!analyze")

    push_message(main_info, "Ran k and !analyze on all threads!\n")


def select_file(sel_type: str):
    """
    File selection prompt and handling

    Args:
        - (str) se_type - The type of path to fetch (Folder or file)
    """
    # Used with the `Select file` button
    if sel_type == "file":
        filetypes = (("ZIP files, DMP files", ("*.zip", "*.dmp")),)
        file_path = filedialog.askopenfilename(filetypes=filetypes)
    # Used with the `Select folder` button
    elif sel_type == "folder":
        file_path = filedialog.askdirectory()

    # If the file path exists, sets the file path box-es value to it
    if file_path:
        file_path_box.configure(state=NORMAL)
        file_path_box.delete(1.0, END)
        file_path_box.insert(END, file_path)

        # Makes you able to load the files once a selection has been made
        load_button.configure(state=NORMAL)


def change_theme():
    """
    Changes the theme to dark mode or light mode according to the jim_toggle value
    """

    # Default black theme
    bg_theme = "#2d2d2d"
    fg_theme = "white"

    # Light mode
    if jim_mode.get():
        dark_style.theme_use("default")
        push_message(main_info, "Light mode enabled, may your eyes burn.\n")
        bg_theme = "white"
        fg_theme = "black"

    # Dark mode
    else:
        dark_style.theme_use("dark")
        push_message(main_info, "Dark mode enabled, welcome home.\n")

    # Updates the main text boxes
    file_path_box.configure(background=bg_theme, foreground=fg_theme)
    main_info.configure(background=bg_theme, foreground=fg_theme)

    # Updates every tabs text boxes
    for file in files:
        prefix = file[:-4]

        globals()[f"{prefix}_window"].configure(
            background=bg_theme, foreground=fg_theme
        )
        globals()[f"{prefix}_command"].configure(
            background=bg_theme, foreground=fg_theme
        )


# -> Main tab definitions <-

root = Tk()
root.geometry("1000x750")
root.title("Tomfoolery (BETA)")


# -> Variables <-

files = {}  # Dump name: Dump path
THREAD_EXECUTE = True  # Used when stopping the program
jim_mode = BooleanVar()

# Gets the CDB path
CDB_PATH = "C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\cdb.exe"

# x64 version check
if not os.path.isfile(CDB_PATH):
    print("x64 version of CDB not installed, falling back to the x32 version...")
    CDB_PATH = "C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x86\\cdb.exe"

    # x32 version check
    if not os.path.isfile(CDB_PATH):
        print(
            "CDB is not installed! Please install the debugging tools from the Windows SDK."
            + "You can install them from: https://go.microsoft.com/fwlink/?linkid=2237387"
        )
        sys.exit()


# -> Style definitions <-

# Defines the colors of the dark theme
dark_theme = {
    ".": {
        "configure": {
            "background": "#212121",
            "foreground": "white",
        }
    },
    "TLabel": {
        "configure": {
            "foreground": "white",
        }
    },
    "TButton": {
        "configure": {
            "background": "#3f4344",
            "foreground": "white",
        },
        "map": {"foreground": [("disabled", "gray")]},
    },
}

# Creates the dark style
dark_style = Style()
dark_style.theme_create("dark", parent="clam", settings=dark_theme)
dark_style.theme_use("dark")  # Applies it


# -> Widget definitions <-

tabControl = Notebook(root)

# Creates the main tab
main_tab = Frame(tabControl)
tabControl.add(main_tab, text="MAIN")
tabControl.pack(expand=1, fill=BOTH)

# Creates the main info window
main_info = Text(
    main_tab, height=15, width=60, background="#2d2d2d", foreground="white"
)
main_info.pack()
main_info.configure(state=DISABLED)


# -- File selection section --

# Creates the frame to contain the file selection widgets
file_path_frame = Frame(main_tab)
file_path_frame.pack(side=BOTTOM, pady=5, padx=10, fill=X)

# Creates box holding the file path, value is pulled from it later
file_path_box = Text(
    file_path_frame, height=1, background="#2d2d2d", foreground="white"
)
file_path_box.pack(side=BOTTOM, fill=X, expand=True)

# Creates the frame to contain buttons
file_buttons_frame = Frame(file_path_frame)
file_buttons_frame.pack(side=BOTTOM)

# Creates the `Select File` button
select_button = Button(
    file_buttons_frame, text="Select File", command=lambda: select_file(sel_type="file")
)
select_button.pack(side=LEFT, padx=5)

# Creates the `Select Folder` button
folder_select_button = Button(
    file_buttons_frame,
    text="Select Folder",
    command=lambda: select_file(sel_type="folder"),
)
folder_select_button.pack(side=LEFT, padx=5)


# -- Running section --

# Creates the frame to contain buttons
button_frame = Frame(main_tab)
button_frame.pack(side=BOTTOM)

# Creates the `Load files` button
load_button = Button(button_frame, text="Load files", command=load_command)
load_button.pack(side=LEFT, padx=5)
load_button.configure(state=DISABLED)

# Creates the `Run k and !analyze` button
run_default_button = Button(
    button_frame, text="Run k and !analyze", command=run_default_commands
)
run_default_button.pack(side=LEFT, padx=5)
run_default_button.configure(state=DISABLED)

# Creates the light mode tick
jim_toggle = Checkbutton(
    main_tab, text="Jim mode", variable=jim_mode, command=change_theme
)
jim_toggle.pack(side=BOTTOM, pady=5)


# -> Argument handling <-

if len(sys.argv) > 1:
    argument = sys.argv[1]

    file_path_box.configure(state=NORMAL)
    file_path_box.delete(1.0, END)
    file_path_box.insert(END, argument)

    # Makes you able to load the files once a selection has been made
    load_button.configure(state=NORMAL)


# -> Window handling <-


def handle_close():
    """
    Stops all threads before exiting the program
    """
    # All threads stop on their next iteration
    global THREAD_EXECUTE
    THREAD_EXECUTE = False
    main_info.insert(END, "Stopping all threads!\n")

    # Joins all threads to the main thread
    for thread in threading.enumerate():
        if thread != threading.main_thread():
            thread.join()

    # Finally, kill the root window and in term all threads
    root.destroy()


root.protocol("WM_DELETE_WINDOW", handle_close)

root.mainloop()
