import os, re, time, json, threading, requests, ctypes, webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk

MAX_WORKERS = 20
BATCH_UPDATE_MS = 100
REQUEST_TIMEOUT = 5

FOUND = {}
SEEN = set()
STOP = threading.Event()
update_queue = Queue()
fetch_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
name_cache = {}
UID_RE = re.compile(r"\[U:1:(\d+)\]")

def steamid64(id3): 
    return 76561197960265728 + id3

def get_name_from_api(key, sid):
    if sid in name_cache:
        name, ts = name_cache[sid]
        if time.time() - ts < 21600:  # 6 hours
            return name
    try:
        r = requests.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": key, "steamids": sid},
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        p = r.json().get("response", {}).get("players", [])
        name = p[0]["personaname"] if p else "<unavailable>"
        name_cache[sid] = (name, time.time())
        return name
    except:
        return "<unavailable>"

def tail_log_file(path, api_key):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, os.SEEK_END)
            while not STOP.is_set():
                line = f.readline()
                if not line: 
                    time.sleep(0.05)
                    continue
                if "IClientFriends::RequestUserInformation" not in line: 
                    continue
                m = UID_RE.search(line)
                if not m: 
                    continue
                acct = m.group(1)
                if acct in SEEN: 
                    continue
                SEEN.add(acct)
                sid = str(steamid64(int(acct)))
                FOUND[sid] = "<loading>"
                update_queue.put((sid, "<loading>", datetime.now().strftime("%H:%M:%S")))
                fetch_executor.submit(fetch_and_queue, api_key, sid)
    except: 
        pass

def fetch_and_queue(api_key, sid):
    FOUND[sid] = get_name_from_api(api_key, sid)
    update_queue.put((sid, FOUND[sid], datetime.now().strftime("%H:%M:%S")))

class ScrollableFrame(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.inner_id, width=e.width))
        
        # Bind mousewheel to canvas directly
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

class RowWidget(ttk.Frame):
    def __init__(self, parent, sid, name, timestamp):
        super().__init__(parent)
        self.sid = sid
        self.name = name
        self.timestamp = timestamp
        self.configure(style="Row.TFrame")

        tk.Button(self, text="/p", width=3, height=1,
                 bg="#555555", fg="#ffffff", bd=0,
                 activebackground="#777777",
                 cursor="hand2",
                 command=self.copy_p).pack(side="left", padx=(2, 6), pady=1)

        self.name_var = tk.StringVar(value=self.name[:32])
        self.name_lbl = tk.Label(self, textvariable=self.name_var,
                                fg="#80c0ff", bg="#1e1e1e",
                                font=("Segoe UI", 10),
                                cursor="hand2")
        self.name_lbl.pack(side="left", padx=(0, 8))
        self.name_lbl.bind("<Button-1>", lambda e: self.open_profile())
        self.name_lbl.bind("<Enter>", lambda e: self.name_lbl.configure(font=("Segoe UI", 10, "underline")))
        self.name_lbl.bind("<Leave>", lambda e: self.name_lbl.configure(font=("Segoe UI", 10)))

        tk.Label(self, text=self.sid, fg="#aaaaaa", bg="#1e1e1e", 
                font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))

        self.time_lbl = tk.Label(self, text=self.timestamp, fg="#aaaaaa", bg="#1e1e1e", 
                                font=("Segoe UI", 9))
        self.time_lbl.pack(side="right", padx=(0, 6))

    def update(self, name, timestamp):
        self.name = name
        self.timestamp = timestamp
        self.name_var.set(self.name[:32])
        self.time_lbl.config(text=self.timestamp)

    def copy_p(self):
        self.master.master.clipboard_clear()
        self.master.master.clipboard_append(f"/p {self.name} ")

    def open_profile(self):
        webbrowser.open(f"https://steamcommunity.com/profiles/{self.sid}")

class App(tk.Tk):
    def __init__(self, api_key, log_path):
        super().__init__()
        self.title("Steam IPC Watcher")
        self.geometry("480x550")
        self.configure(bg="#1e1e1e")
        self.attributes("-topmost", True)

        # Apply Windows always-on-top
        try:
            if os.name == "nt":
                self.update_idletasks()
                ctypes.windll.user32.SetWindowPos(
                    ctypes.windll.user32.GetForegroundWindow(),
                    -1, 0, 0, 0, 0, 0x0001 | 0x0002
                )
        except: 
            pass

        # Styles
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("Row.TFrame", background="#1e1e1e")
        style.configure("TButton",
                       background="#2e2e2e",
                       foreground="#ffffff",
                       font=("Segoe UI", 10, "bold"),
                       borderwidth=0)
        style.map("TButton",
                 background=[('active', '#444444')],
                 foreground=[('active', '#ffffff')])

        # Top bar
        topbar = tk.Frame(self, bg="#2b2b2b", height=36)
        topbar.pack(side="top", fill="x", padx=4, pady=4)

        tk.Button(topbar,
                 text="Clear",
                 command=self.clear_all,
                 bg="#ff5555",
                 fg="#ffffff",
                 activebackground="#ff7777",
                 activeforeground="#ffffff",
                 font=("Segoe UI", 10, "bold"),
                 bd=0,
                 padx=12,
                 pady=4,
                 cursor="hand2").pack(side="right", padx=4)

        # Scrollable frame
        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)

        self.rows = {}

        self.api_key = api_key
        self.log_path = log_path

        threading.Thread(target=tail_log_file, 
                        args=(self.log_path.replace("\\\\", "\\"), self.api_key), 
                        daemon=True).start()

        self.after(BATCH_UPDATE_MS, self.process_updates)

    def process_updates(self):
        try:
            while True:
                sid, name, timestamp = update_queue.get_nowait()
                if sid in self.rows:
                    self.rows[sid].update(name, timestamp)
                else:
                    row = RowWidget(self.scroll_frame.inner, sid, name, timestamp)
                    row.pack(fill="x", padx=2, pady=1)
                    self.rows[sid] = row
        except Empty: 
            pass
        self.after(BATCH_UPDATE_MS, self.process_updates)

    def clear_all(self):
        FOUND.clear()
        SEEN.clear()
        name_cache.clear()
        for child in list(self.scroll_frame.inner.winfo_children()): 
            child.destroy()
        self.rows.clear()

def load_config():
    cfg = {}
    if os.path.exists("config.json"):
        try: 
            cfg = json.load(open("config.json", "r", encoding="utf-8"))
        except: 
            pass
    return cfg

def main():
    print("Run: steam://open/console")
    print("In Steam console: log_ipc 1")
    input("Press Enter when ready...")
    
    cfg = load_config()
    api_key = cfg.get("api_key", "")
    log_path = cfg.get("log_path", "")
    
    App(api_key, log_path).mainloop()

if __name__ == "__main__": 
    main()