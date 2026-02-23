from tkinter import *
from tkinter import simpledialog, messagebox
from datetime import datetime
import time
import json
from netutils import *

username = None
password = None

# loading app data using json file
with open("messenger.json", "r") as data:
    MESSENGER = json.load(data)
    
FILTER_WORDS = MESSENGER["filter_words"]
USERS = MESSENGER["users"]

# Theme colors (dynamic) -> may change later when user change theme color
# We initialize our program theme with dark mode user can change this later in messenger app preferences

TC1, TC2, TC3 = "#18191A", "#242526", "#303136" # main program background palette
FG, HIGHLIGHT = "#F5F0F0", "#8848EE" # commonly used as foreground and main texts
BTN_BG, BTN_ACTIVE = "#2C2C2C", "#301441"

# Globals
sock = None
addr = None
connected = True # we assume connection to be succesfully actived in the start
sent_count = 0
recv_count = 0
start_time = None
window = None # our main messenger window
startup_window = None # this prompts for guest / host selection
chat_box = None
entry = None
send_btn = None
quit_btn = None
status = None
mode = None # guest/host
shift = 13 # initial shift -> it can be changed using change shift in program menu
auto_send_timer = None
custom_encode_label = None
custom_encode_mode = False


btn_style = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
             "activeforeground": FG, "width": 14, "highlightthickness": 0, "bd": 3, "cursor": "hand2"}
btn_style2 = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
              "activeforeground": FG, "width": 8, "font": ("Segoe UI", 10), "bd": 0, "highlightthickness": 0, "cursor": "hand2"}

def runApp():
    global username, password
    global window, sock, addr, start_time, mode, startup_window, username
    window = Tk()
    window.title("Messenger")
    window.configure(bg=TC1)
    window.withdraw()
    window.minsize(width=350, height=500) 
    window.geometry("400x550")
    
    # Prompt for login
    username, password = login_user(window,USERS)
    if username is None:
        return  # User cancelled

    # Now that login was successfully its time for mode selection
    select_mode() # -> assigns global variable [mode] guest/host
    
    if mode == "host":
        print("Mode specified: Host")
        port = simpledialog.askinteger("Host Settings", "Choose port:", initialvalue=55555, parent=window)
        sock, addr = setup_server(port)
        window.title("Host Window")
        if not sock:
            messagebox.showerror("Error", "Socket Error.")
            window.destroy()
            return
    elif mode == "guest":
        print("Mode specified: Guest")
        window.title("Guest Window")
        ip_add = simpledialog.askstring("Guest Settings", "Enter Host IP:", initialvalue="127.0.0.1", parent=window)
        port = simpledialog.askinteger("Guest Settings", "Enter Host port:", initialvalue=55555, parent=window)
        addr = (ip_add, port)
        sock = setup_client(ip_add, port)
        
        if not sock:
            messagebox.showerror("Error", "Connection failed.")
            window.destroy()
            return

    window.deiconify() # Shows window again since socket was stablished successfully
    build_ui()
    start_time = time.time() # Starts timer right after our messenger ui is built
    window.protocol("WM_DELETE_WINDOW", quit_handler) # handling safe shutdown as project requirements
    window.after(500, check_for_messages) # add interval to check for new message in entry every 500ms
    window.mainloop()


def select_mode():
    global mode, startup_window
    startup_window = Toplevel(bg=TC1)
    startup_window.title("Mode Selection")
    startup_window.geometry("320x190")
    startup_window.resizable(False, False)
    startup_window.grab_set()

    lbl = Label(startup_window, text="Continue as Host or Guest:", bg=TC1, fg=FG)
    lbl.pack(pady=20, side="top", anchor="center")
    guest_btn = Button(startup_window, text="Guest", command=guest_select, **btn_style)
    guest_btn.pack(pady=5)
    host_btn = Button(startup_window, text="Host", command=host_select, **btn_style)
    host_btn.pack(pady=5)

    window.wait_window(startup_window)
    startup_window.destroy()
    if not mode: # allow user to retry for mode selection for infinite amount of time
        retry = messagebox.askretrycancel(title="Error", message="No mode was selected.")
        if retry:
            select_mode()
        else:
            window.destroy()

def guest_select():
    global mode, startup_window
    mode = "guest"
    startup_window.destroy()

def host_select():
    global mode, startup_window
    mode = "host"
    startup_window.destroy()

def build_ui():
    global chat_box, entry, send_btn, quit_btn, status, custom_encode_label

    def toggle_custom_encoding():
        global custom_encode_mode, custom_encode_label
        custom_encode_mode = not custom_encode_mode
        if custom_encode_mode:
            custom_encode_label.config(text="custom_encode Mode ON")
            messagebox.showinfo("custom_encode Mode", "custom_encode mode is ON.\nMessages you send will be logged using my custom symmetrical encoding method from now on.")
            system_msg("Custom encode mode toggled.")
            
        else:
            custom_encode_label.config(text="")
            messagebox.showinfo("custom_encode Mode", "custom_encode mode is OFF. Messages are logged as usual.")
    
    txt_scrollbar_frame = Frame(window, bg=TC2, takefocus=False)
    txt_scrollbar_frame.pack(side="top", expand=True, fill="both")
    chat_box = Text(txt_scrollbar_frame, state='disabled', bg=TC2, fg=HIGHLIGHT, insertbackground=HIGHLIGHT,bd=0, highlightthickness=0, selectbackground=HIGHLIGHT, selectforeground=FG)
    scrollbar = Scrollbar(txt_scrollbar_frame, command=chat_box.yview, troughcolor=TC2, highlightcolor=HIGHLIGHT, bd=0, cursor="hand2")
    scrollbar.pack(side="right", expand=True, fill="y")
    chat_box.pack(side="left", padx=10, pady=10, expand=True, fill="both")
    frame = Frame(window, bg=TC1)
    frame.pack(expand=True, fill='x')

    entry = Entry(frame, bg=TC3, fg=HIGHLIGHT, insertbackground=HIGHLIGHT, bd=0,highlightthickness=2, highlightcolor=HIGHLIGHT, font=("Segoe UI", 11),selectbackground=HIGHLIGHT, selectforeground=FG)
    entry.pack(side='left', padx=10, pady=10, expand=True, fill="x")
    
    entry.bind("<Return>", send_handler) # Send message on Enter
    entry.bind("<Key>", user_key_handler) # user_key_handler resets 30 second interval for message auto-send

    send_btn = Button(frame, text="Send", command=send_handler, **btn_style2)
    send_btn.pack(side='left', padx=5)
    quit_btn = Button(frame, text="Quit", command=quit_handler, **btn_style2)
    quit_btn.pack(side='left', padx=5)

    status = Label(window, text="Sent: 0 | Received: 0", bg=TC1, fg=HIGHLIGHT, font=("Segoe UI", 10))
    status.pack(side='bottom', pady=6)
    custom_encode_label = Label(window, text="", bg=TC1, fg="red", font=("Segoe UI", 9))
    custom_encode_label.pack(side='bottom')

    menu = Menu(window, bd=0)
    menu.add_command(label="Change Shift", command=change_shift)
    preferences = Menu(menu, tearoff=0)
    preferences.add_command(label="Light Mode", command=lambda: turn_light())
    preferences.add_command(label="Dark Mode", command=lambda: turn_dark())
    preferences.add_command(label="Toggle Custom Encoding", command=lambda: toggle_custom_encoding())
    info = Menu(menu, tearoff= 0)
    info.add_command(label="Made by:", state="disabled")
    info.add_command(label="Roghayeh Saadabadi", state="disabled")
    info.add_command(label="Student ID:", state="disabled")
    info.add_command(label="40332339", state="disabled")
    window.config(menu=menu)
    menu.add_cascade(label="Preferences", menu=preferences)
    menu.add_cascade(label="About",menu=info)
    

    def turn_light():
        global TC1, TC2, TC3, FG, HIGHLIGHT, BTN_BG, BTN_ACTIVE, btn_style, btn_style2
        TC1, TC2, TC3 = "#fff", "#f2f2f2", "#e0e5ee"
        FG, HIGHLIGHT = "#242526", "#FF0055"
        BTN_BG, BTN_ACTIVE = "#f2f2f2", "#e0e5ee"
        btn_style = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
             "activeforeground": FG, "width": 14, "highlightthickness": 0, "bd": 3, "cursor": "hand2"}
        btn_style2 = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
              "activeforeground": FG, "width": 8, "font": ("Segoe UI", 10), "bd": 0, "highlightthickness": 0, "cursor": "hand2"}
        system_msg("Theme changed to light mode.")
        apply_theme()

    def turn_dark():
        global TC1, TC2, TC3, FG, HIGHLIGHT, BTN_BG, BTN_ACTIVE,btn_style, btn_style2
        TC1, TC2, TC3 = "#18191A", "#242526", "#303136"
        FG, HIGHLIGHT = "#F5F0F0", "#8848EE"
        BTN_BG, BTN_ACTIVE = "#2C2C2C", "#301441"
        btn_style = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
             "activeforeground": FG, "width": 14, "highlightthickness": 0, "bd": 3, "cursor": "hand2"}
        btn_style2 = {"bg": BTN_BG, "fg": HIGHLIGHT, "activebackground": BTN_ACTIVE,
              "activeforeground": FG, "width": 8, "font": ("Segoe UI", 10), "bd": 0, "highlightthickness": 0, "cursor": "hand2"}
        system_msg("Theme changed to dark mode.")
        apply_theme()

    def apply_theme():
        global btn_style, btn_style2
        txt_scrollbar_frame.config(bg=TC2)
        chat_box.configure(bg=TC2, fg=HIGHLIGHT, selectbackground=HIGHLIGHT, selectforeground=FG)
        frame.configure(bg=TC1)
        window.configure(bg=TC1)
        entry.config(bg=TC3, fg=HIGHLIGHT, insertbackground=HIGHLIGHT, highlightcolor=HIGHLIGHT,
                     selectbackground=HIGHLIGHT, selectforeground=FG)
        status.config(bg=TC1, fg=HIGHLIGHT)
        send_btn.config(**btn_style2)
        quit_btn.config(**btn_style2)
        custom_encode_label.config(bg=TC1)
        

def send_handler(event=None):
    global sent_count, auto_send_timer, username, custom_encode_mode
    if auto_send_timer is not None:
        try:
            window.after_cancel(auto_send_timer) # resets timer since send button is triggered
        except Exception:
            print("Window.after_cancel failed resetting timer")
        auto_send_timer = None
    msg = str(entry.get()).strip()
    if msg == '':
        return # doesnt send empty messages for cleaner look
    for blocked_word in FILTER_WORDS:
        if blocked_word.lower() in msg.lower():
            messagebox.showwarning("Blocked Word Usage", f"Using word '{blocked_word}' is forbidden")
            entry.delete(0, END) # clears entry
            return
    try:
        send_message(sock, msg, shift, username, custom_encode_mode)
        sent_count += 1
        if not msg.startswith("!!"):
            append_chat(f"{str(username)} ({timestamp1()}): {msg}")
        update_status()
    except Exception:
        messagebox.showerror("Error", "Failed to send message.")
    entry.delete(0, END)

def check_for_messages():
    global recv_count, shift, custom_encode_mode, username
    if connected:
        try:
            msg = receive_message(sock, shift, username, custom_encode_mode)
            if msg:
                if not msg.startswith("!!"):
                    append_chat(f"Peer ({timestamp1()}): {msg}")
                recv_count += 1
                update_status()
        except Exception:
            pass
    window.after(500, check_for_messages)

def append_chat(text):
    chat_box.config(state='normal') # this enables content insersion
    chat_box.insert('end', text + "\n")
    chat_box.config(state='disabled') 
    chat_box.see('end') # scroll down to chat_box end like real messenger

def timestamp1():
    return datetime.now().strftime("%H:%M:%S")
def timestamp2():
    return datetime.now().strftime("%Y-%m-%d")

def change_shift():
    global shift
    s = simpledialog.askinteger("Change Cipher Shift", "Enter shift value (1-25):", initialvalue=shift, parent=window)
    if s and 1 <= s < 26:
        shift = s
        system_msg("SHIFT CHANGED")
    elif s == None: # in case user cancels shift changing
        pass
    else:
        messagebox.showerror("Error", "Shift must be between 1 and 25.")

def update_status():
    status.config(text=f"Sent: {sent_count} | Received: {recv_count}")

def quit_handler():
    duration = int(time.time() - start_time)
    mins = duration // 60   # total minutes
    seconds = duration % 60    # seconds left
    messagebox.showinfo(
        "Session Summary",
        f"Session duration: {mins} minutes and {seconds} seconds\n"
        f"Number of messages sent: {sent_count}\n"
        f"Number of messages received: {recv_count}")
    close_socket(sock)
    window.destroy()

def user_key_handler(event=None):
    global auto_send_timer
    if auto_send_timer is not None:
        try:
            window.after_cancel(auto_send_timer)
        except Exception:
            pass
    auto_send_timer = window.after(30000, send_handler)  # 30 seconds

def login_user(window, users):
    while True:
        username = simpledialog.askstring("Login", "Username:",parent = window)
        if username is None:
            return None, None  # User cancelled

        password = simpledialog.askstring("Login", "Password:", show="*", parent=window)
        if password is None:
            return None, None

        # Validate from JSON
        for u in users:
            if u["username"] == username and u["password"] == password:
                return username, password
        messagebox.showerror("Login Error", "Incorrect username or password. Try again.")
        
        
def system_msg(msg):
    append_chat(f"SYSTEM: ({timestamp1()}): {msg}")
