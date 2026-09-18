import os
import sys
import json
import math
import subprocess
import threading
import queue
import time
import urllib.request
import urllib.parse
import zipfile
import shutil
import re
import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Resource path helper for PyInstaller bundled files
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Windows sound notification handling
if sys.platform == "win32":
    try:
        import winsound
    except ImportError:
        winsound = None
else:
    winsound = None

# --- THEMES DEFINITION ---
THEMES = {
    "Greedy Occult": {
        "bg": "#12090b", "fg": "#ff4d4d", "card_bg": "#1d0e13",
        "btn_bg": "#3a131a", "btn_fg": "#ff8080", "accent": "#ff1a40",
        "entry_bg": "#ffffff", "log_bg": "#090305", "highlight": "#8b0022"
    },
    "Cyberpunk Neon": {
        "bg": "#0f0e17", "fg": "#00f5d4", "card_bg": "#1b192b",
        "btn_bg": "#2e2b44", "btn_fg": "#f72585", "accent": "#f72585",
        "entry_bg": "#ffffff", "log_bg": "#090810", "highlight": "#7209b7"
    },
    "Default Dark Mint": {
        "bg": "#11111b", "fg": "#a6e3a1", "card_bg": "#181825",
        "btn_bg": "#1e2e1e", "btn_fg": "#a6e3a1", "accent": "#a6e3a1",
        "entry_bg": "#ffffff", "log_bg": "#0d1117", "highlight": "#314d31"
    },
    "macOS Light": {
        "bg": "#f0f0f3", "fg": "#1d1d1f", "card_bg": "#ffffff",
        "btn_bg": "#e1e1e6", "btn_fg": "#1d1d1f", "accent": "#007aff",
        "entry_bg": "#ffffff", "log_bg": "#f5f5f7", "highlight": "#007aff"
    },
    "Dracula Slate": {
        "bg": "#282a36", "fg": "#f8f8f2", "card_bg": "#44475a",
        "btn_bg": "#6272a4", "btn_fg": "#f8f8f2", "accent": "#bd93f9",
        "entry_bg": "#ffffff", "log_bg": "#1e1f29", "highlight": "#bd93f9"
    },
    "Nordic Frost": {
        "bg": "#2e3440", "fg": "#eceff4", "card_bg": "#3b4252",
        "btn_bg": "#434c5e", "btn_fg": "#eceff4", "accent": "#88c0d0",
        "entry_bg": "#ffffff", "log_bg": "#232831", "highlight": "#5e81ac"
    },
    "Synthwave '84": {
        "bg": "#241b2f", "fg": "#f3e8ff", "card_bg": "#2a2139",
        "btn_bg": "#3c2e50", "btn_fg": "#ff7edb", "accent": "#fe4450",
        "entry_bg": "#ffffff", "log_bg": "#1a1322", "highlight": "#36f9f6"
    }
}

class PlaceholderEntry(ttk.Entry):
    def __init__(self, container, placeholder="Show Name", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = "#888888"
        self.default_fg = "#000000"

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)

        self._add_placeholder()

    def _clear_placeholder(self, e):
        if self.get() == self.placeholder:
            super().delete(0, tk.END)
            self.configure(foreground=self.default_fg)

    def _add_placeholder(self, e=None):
        if not self.get().strip():
            self.configure(foreground=self.placeholder_color)
            super().insert(0, self.placeholder)

    def get_query(self):
        val = super().get().strip()
        if val == self.placeholder:
            return ""
        return val


class BulkRenameAndFolderDialog(tk.Toplevel):
    def __init__(self, parent, items_data, current_theme):
        super().__init__(parent)
        self.title("🛠️ Bulk Renaming & Folder Creator Suite")
        self.geometry("940x800")
        self.minsize(820, 640)
        self.theme = current_theme
        self.configure(bg=self.theme["bg"])

        self.items_data = items_data
        self.result = None
        self.rename_disk_immediately = False
        self.target_parent_dir = ""

        self._build_ui()
        self.transient(parent)
        self.grab_set()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Tab 1: Classic Bulk Renamer
        self.renamer_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.renamer_tab, text="🛠️ Classic Bulk Renamer")
        self._build_renamer_tab(self.renamer_tab)

        # Tab 2: Bulk Folder Creator
        self.folder_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.folder_tab, text="📁 Bulk Folder Creator")
        self._build_folder_tab(self.folder_tab)

    def _build_renamer_tab(self, tab):
        tab.columnconfigure(1, weight=1)

        del_frame = ttk.LabelFrame(tab, text=" Simplified Character Deletion ", padding=8)
        del_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        del_frame.columnconfigure(1, weight=1)
        del_frame.columnconfigure(3, weight=1)

        ttk.Label(del_frame, text="Delete Front (Chars):").grid(row=0, column=0, sticky="w", pady=2)
        self.del_front_var = tk.StringVar(value="0")
        self.del_front_var.trace_add("write", self._update_renamer_preview)
        ttk.Spinbox(del_frame, from_=0, to=100, textvariable=self.del_front_var, width=6, foreground="#000000").grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(del_frame, text="Delete Back (Chars):").grid(row=0, column=2, sticky="w", pady=2)
        self.del_back_var = tk.StringVar(value="0")
        self.del_back_var.trace_add("write", self._update_renamer_preview)
        ttk.Spinbox(del_frame, from_=0, to=100, textvariable=self.del_back_var, width=6, foreground="#000000").grid(row=0, column=3, sticky="w", padx=4, pady=2)

        ttk.Label(del_frame, text="Delete From Index:").grid(row=1, column=0, sticky="w", pady=(6, 2))
        self.del_from_var = tk.StringVar(value="0")
        self.del_from_var.trace_add("write", self._update_renamer_preview)
        ttk.Spinbox(del_frame, from_=0, to=100, textvariable=self.del_from_var, width=6, foreground="#000000").grid(row=1, column=1, sticky="w", padx=4, pady=(6, 2))

        ttk.Label(del_frame, text="Delete To Index:").grid(row=1, column=2, sticky="w", pady=(6, 2))
        self.del_to_var = tk.StringVar(value="0")
        self.del_to_var.trace_add("write", self._update_renamer_preview)
        ttk.Spinbox(del_frame, from_=0, to=100, textvariable=self.del_to_var, width=6, foreground="#000000").grid(row=1, column=3, sticky="w", padx=4, pady=(6, 2))

        ttk.Label(tab, text="Add Prefix:").grid(row=1, column=0, sticky="w", pady=4)
        self.prefix_var = tk.StringVar()
        self.prefix_var.trace_add("write", self._update_renamer_preview)
        ttk.Entry(tab, textvariable=self.prefix_var, foreground="#000000").grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(tab, text="Add Suffix (Before Ext):").grid(row=2, column=0, sticky="w", pady=4)
        self.suffix_var = tk.StringVar()
        self.suffix_var.trace_add("write", self._update_renamer_preview)
        ttk.Entry(tab, textvariable=self.suffix_var, foreground="#000000").grid(row=2, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(tab, text="Find Text:").grid(row=3, column=0, sticky="w", pady=4)
        self.find_var = tk.StringVar()
        self.find_var.trace_add("write", self._update_renamer_preview)
        ttk.Entry(tab, textvariable=self.find_var, foreground="#000000").grid(row=3, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(tab, text="Replace With:").grid(row=4, column=0, sticky="w", pady=4)
        self.replace_var = tk.StringVar()
        self.replace_var.trace_add("write", self._update_renamer_preview)
        ttk.Entry(tab, textvariable=self.replace_var, foreground="#000000").grid(row=4, column=1, sticky="ew", padx=4, pady=4)

        self.regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="Use Regular Expressions (Regex)", variable=self.regex_var, command=self._update_renamer_preview).grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 6))

        ttk.Label(tab, text="Case Conversion:").grid(row=6, column=0, sticky="w", pady=4)
        self.case_var = tk.StringVar(value="None (Keep Original)")
        case_options = ["None (Keep Original)", "Title Case", "UPPERCASE", "lowercase"]
        case_cb = ttk.Combobox(tab, textvariable=self.case_var, values=case_options, state="readonly", width=28)
        case_cb.grid(row=6, column=1, sticky="w", padx=4, pady=4)
        case_cb.bind("<<ComboboxSelected>>", self._update_renamer_preview)

        preview_frame = ttk.LabelFrame(tab, text=" Live Bulk Rename Preview ", padding=6)
        preview_frame.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(4, 8))
        tab.rowconfigure(7, weight=1)

        cols = ("orig", "new")
        self.renamer_tree = ttk.Treeview(preview_frame, columns=cols, show="headings")
        self.renamer_tree.heading("orig", text="Original Filename")
        self.renamer_tree.heading("new", text="Renamed Preview")
        self.renamer_tree.column("orig", width=300, anchor="w")
        self.renamer_tree.column("new", width=440, anchor="w")

        scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.renamer_tree.yview)
        self.renamer_tree.configure(yscroll=scroll.set)
        self.renamer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_box = ttk.Frame(tab)
        btn_box.grid(row=8, column=0, columnspan=2, sticky="e")

        ttk.Button(btn_box, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="Apply Names to Queue", style="Accent.TButton", command=self._apply_queue).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="⚡ Rename Files on Disk", style="Accent.TButton", command=self._apply_disk_now).pack(side=tk.RIGHT)

        self._update_renamer_preview()

    def _update_renamer_preview(self, *args):
        if not hasattr(self, "renamer_tree") or not self.renamer_tree.winfo_exists():
            return
        self.renamer_tree.delete(*self.renamer_tree.get_children())
        prefix = self.prefix_var.get()
        suffix = self.suffix_var.get()
        find_txt = self.find_var.get()
        replace_txt = self.replace_var.get()
        use_regex = self.regex_var.get()
        case_mode = self.case_var.get()

        try:
            del_front = int(self.del_front_var.get())
        except ValueError:
            del_front = 0
        try:
            del_back = int(self.del_back_var.get())
        except ValueError:
            del_back = 0
        try:
            del_from = int(self.del_from_var.get())
        except ValueError:
            del_from = 0
        try:
            del_to = int(self.del_to_var.get())
        except ValueError:
            del_to = 0

        self.preview_map = []
        for item in self.items_data:
            orig = item["name"]
            base, ext = os.path.splitext(orig)

            if del_front > 0 and len(base) > del_front:
                base = base[del_front:]
            if del_back > 0 and len(base) > del_back:
                base = base[:-del_back]

            if del_to > del_from >= 0 and len(base) >= del_to:
                base = base[:del_from] + base[del_to:]

            if find_txt:
                try:
                    if use_regex:
                        base = re.sub(find_txt, replace_txt, base)
                    else:
                        base = base.replace(find_txt, replace_txt)
                except Exception:
                    pass

            final_base = f"{prefix}{base}{suffix}"
            if "Title Case" in case_mode:
                final_base = final_base.title()
            elif "UPPERCASE" in case_mode:
                final_base = final_base.upper()
            elif "lowercase" in case_mode:
                final_base = final_base.lower()

            new_name = f"{final_base}{ext}"
            self.preview_map.append({"item_id": item["item_id"], "path": item["path"], "new_name": new_name})
            self.renamer_tree.insert("", tk.END, values=(orig, new_name))

    def _apply_queue(self):
        self.rename_disk_immediately = False
        self.result = self.preview_map
        self.destroy()

    def _apply_disk_now(self):
        if messagebox.askyesno("Confirm", "Rename files on disk now?", parent=self):
            self.rename_disk_immediately = True
            self.result = self.preview_map
            self.destroy()

    def _build_folder_tab(self, tab):
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Target Parent Directory:").grid(row=0, column=0, sticky="w", pady=4)
        self.dir_var = tk.StringVar(value="[No folder selected - Click Browse]")
        ttk.Entry(tab, textvariable=self.dir_var, state="readonly", foreground="#000000").grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(tab, text="Browse...", command=self._select_parent_dir).grid(row=0, column=2, padx=4, pady=4)

        settings_frame = ttk.LabelFrame(tab, text=" Folder Naming & Numbering Rules ", padding=8)
        settings_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Base Name / Prefix:").grid(row=0, column=0, sticky="w", pady=4)
        self.folder_prefix_var = tk.StringVar(value="Season ")
        self.folder_prefix_var.trace_add("write", self._update_folder_preview)
        ttk.Entry(settings_frame, textvariable=self.folder_prefix_var, foreground="#000000").grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(settings_frame, text="Starting Number:").grid(row=1, column=0, sticky="w", pady=4)
        self.start_num_var = tk.StringVar(value="1")
        self.start_num_var.trace_add("write", self._update_folder_preview)
        ttk.Spinbox(settings_frame, from_=0, to=9999, textvariable=self.start_num_var, width=8, foreground="#000000").grid(row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(settings_frame, text="Total Count of Folders:").grid(row=2, column=0, sticky="w", pady=4)
        self.count_var = tk.StringVar(value="12")
        self.count_var.trace_add("write", self._update_folder_preview)
        ttk.Spinbox(settings_frame, from_=1, to=500, textvariable=self.count_var, width=8, foreground="#000000").grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(settings_frame, text="Number Zero Padding:").grid(row=3, column=0, sticky="w", pady=4)
        self.folder_padding_var = tk.StringVar(value="2 Digits (01, 02)")
        pad_cb = ttk.Combobox(settings_frame, textvariable=self.folder_padding_var, values=["None (1, 2, 3)", "2 Digits (01, 02)", "3 Digits (001, 002)"], state="readonly", width=22)
        pad_cb.grid(row=3, column=1, sticky="w", padx=4, pady=4)
        pad_cb.bind("<<ComboboxSelected>>", self._update_folder_preview)

        ttk.Label(settings_frame, text="Suffix (Optional):").grid(row=4, column=0, sticky="w", pady=4)
        self.folder_suffix_var = tk.StringVar(value="")
        self.folder_suffix_var.trace_add("write", self._update_folder_preview)
        ttk.Entry(settings_frame, textvariable=self.folder_suffix_var, foreground="#000000").grid(row=4, column=1, sticky="ew", padx=4, pady=4)

        preview_frame = ttk.LabelFrame(tab, text=" Generated Folders Preview ", padding=6)
        preview_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        tab.rowconfigure(2, weight=1)

        cols = ("idx", "foldername")
        self.folder_tree = ttk.Treeview(preview_frame, columns=cols, show="headings")
        self.folder_tree.heading("idx", text="#")
        self.folder_tree.heading("foldername", text="Folder Name Preview")
        self.folder_tree.column("idx", width=50, anchor="center")
        self.folder_tree.column("foldername", width=480, anchor="w")

        scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.folder_tree.yview)
        self.folder_tree.configure(yscroll=scroll.set)
        self.folder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_box = ttk.Frame(tab)
        btn_box.grid(row=3, column=0, columnspan=3, sticky="e")

        ttk.Button(btn_box, text="📁 Create Folders Now", style="Accent.TButton", command=self._create_folders_on_disk).pack(side=tk.RIGHT)

        self._update_folder_preview()

    def _select_parent_dir(self):
        chosen = filedialog.askdirectory(title="Select Parent Directory for Bulk Folders")
        if chosen:
            self.target_parent_dir = chosen
            self.dir_var.set(chosen)

    def _update_folder_preview(self, *args):
        if not hasattr(self, "folder_tree") or not self.folder_tree.winfo_exists():
            return
        self.folder_tree.delete(*self.folder_tree.get_children())
        prefix = self.folder_prefix_var.get()
        suffix = self.folder_suffix_var.get()
        padding_mode = self.folder_padding_var.get()

        try:
            start_num = int(self.start_num_var.get())
        except ValueError:
            start_num = 1

        try:
            count = int(self.count_var.get())
        except ValueError:
            count = 1

        self.preview_names = []
        for i in range(count):
            curr_num = start_num + i
            if "2 Digits" in padding_mode:
                num_str = f"{curr_num:02d}"
            elif "3 Digits" in padding_mode:
                num_str = f"{curr_num:03d}"
            else:
                num_str = str(curr_num)

            folder_name = f"{prefix}{num_str}{suffix}"
            self.preview_names.append(folder_name)
            self.folder_tree.insert("", tk.END, values=(i + 1, folder_name))

    def _create_folders_on_disk(self):
        if not self.target_parent_dir or not os.path.exists(self.target_parent_dir):
            messagebox.showwarning("Parent Directory Missing", "Please select a valid parent directory first.", parent=self)
            return

        ans = messagebox.askyesno(
            "Confirm Folder Creation",
            f"Create {len(self.preview_names)} folder(s) inside:\n{self.target_parent_dir}\n\nProceed?",
            parent=self
        )
        if not ans:
            return

        created_count = 0
        existing_count = 0
        for name in self.preview_names:
            full_path = os.path.join(self.target_parent_dir, name)
            try:
                if not os.path.exists(full_path):
                    os.makedirs(full_path, exist_ok=True)
                    created_count += 1
                else:
                    existing_count += 1
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create folder '{name}': {e}", parent=self)
                return

        messagebox.showinfo("Success", f"Successfully created {created_count} folder(s) ({existing_count} already existed).", parent=self)


class SmartTVDBRenamerDialog(tk.Toplevel):
    def __init__(self, parent, items_data, current_theme, parent_app=None):
        super().__init__(parent)
        self.title("🌐 Smart TVDB Renamer")
        self.geometry("980x860")
        self.minsize(820, 640)
        self.theme = current_theme
        self.configure(bg=self.theme["bg"])
        self.parent_app = parent_app

        self.items_data = items_data
        self.result = None
        self.rename_disk_immediately = False
        self.fetched_episodes_list = []
        self.resolved_show_name = ""
        self.preview_map = []

        self._build_ui()
        self._load_dialog_settings()
        self.transient(parent)
        self.grab_set()

    def _load_dialog_settings(self):
        if self.parent_app and hasattr(self.parent_app, "renamer_settings"):
            s = self.parent_app.renamer_settings
            if s.get("query"):
                self.query_entry.delete(0, tk.END)
                self.query_entry.configure(foreground=self.query_entry.default_fg)
                self.query_entry.insert(0, s["query"])
            if s.get("tvdb_api_key"):
                self.apikey_entry.delete(0, tk.END)
                self.apikey_entry.insert(0, s["tvdb_api_key"])
            if s.get("padding"):
                self.padding_var.set(s["padding"])
            if s.get("separator"):
                self.sep_var.set(s["separator"])
            if "include_title" in s:
                self.include_title_var.set(s["include_title"])
            if s.get("start_season"):
                self.start_season_var.set(s["start_season"])
            if s.get("start_ep"):
                self.start_ep_var.set(s["start_ep"])
        self._update_preview()

    def _save_dialog_settings(self):
        if self.parent_app:
            self.parent_app.renamer_settings = {
                "query": self.query_entry.get_query(),
                "tvdb_api_key": self.apikey_entry.get().strip(),
                "padding": self.padding_var.get(),
                "separator": self.sep_var.get(),
                "include_title": self.include_title_var.get(),
                "start_season": self.start_season_var.get(),
                "start_ep": self.start_ep_var.get()
            }
            self.parent_app.save_settings()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="TheTVDB API Key (v4):").grid(row=0, column=0, sticky="w", pady=4)
        
        apikey_box_frame = ttk.Frame(main_frame)
        apikey_box_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        apikey_box_frame.columnconfigure(0, weight=1)

        self.apikey_entry = ttk.Entry(apikey_box_frame, show="*", foreground="#000000")
        self.apikey_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        apikey_paste_btn = ttk.Button(apikey_box_frame, text="📋 Paste", width=8, command=self._paste_apikey)
        apikey_paste_btn.grid(row=0, column=1, sticky="e")

        ttk.Label(main_frame, text="(Required for Official TVDB v4)", foreground="#888888").grid(row=0, column=2, sticky="w", padx=4)

        ttk.Label(main_frame, text="Show Name or TVDB ID:").grid(row=1, column=0, sticky="w", pady=4)
        
        query_box_frame = ttk.Frame(main_frame)
        query_box_frame.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        query_box_frame.columnconfigure(0, weight=1)

        self.query_entry = PlaceholderEntry(query_box_frame, placeholder="e.g. One Piece or Breaking Bad")
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.query_entry.bind("<KeyRelease>", lambda e: self._update_preview())

        paste_btn = ttk.Button(query_box_frame, text="📋 Paste", width=8, command=self._paste_query)
        paste_btn.grid(row=0, column=1, sticky="e")

        fetch_btn = ttk.Button(main_frame, text="🌐 Fetch English TVDB v4", style="Accent.TButton", command=self._fetch_tvdb_metadata)
        fetch_btn.grid(row=1, column=2, padx=4, pady=4)

        self.status_lbl = ttk.Label(main_frame, text="Status: Ready. Enter your TVDB API key and query to fetch English canonical data ✅", foreground="#ff8080")
        self.status_lbl.grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 8))

        se_frame = ttk.LabelFrame(main_frame, text=" Formatting & Sequence Starting Options ", padding=8)
        se_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        ttk.Label(se_frame, text="Zero Padding:").grid(row=0, column=0, sticky="w", pady=2)
        self.padding_var = tk.StringVar(value="2 Digits (E01, E02)")
        padding_cb = ttk.Combobox(se_frame, textvariable=self.padding_var, values=["2 Digits (E01, E02)", "3 Digits (E001, E002)"], state="readonly", width=20)
        padding_cb.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        padding_cb.bind("<<ComboboxSelected>>", self._update_preview)

        self.include_title_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(se_frame, text="Include Fetched English Episode Title", variable=self.include_title_var, command=self._update_preview).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Label(se_frame, text="Separator:").grid(row=1, column=2, sticky="w", pady=2)
        self.sep_var = tk.StringVar(value=" - ")
        sep_cb = ttk.Combobox(se_frame, textvariable=self.sep_var, values=[" - ", " _ ", ". ", " ["], width=10)
        sep_cb.grid(row=1, column=3, sticky="w", padx=4, pady=2)
        sep_cb.bind("<<ComboboxSelected>>", self._update_preview)

        ttk.Label(se_frame, text="Start Season (Un-tagged fallback):").grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.start_season_var = tk.StringVar(value="1")
        start_season_spin = ttk.Spinbox(se_frame, from_=1, to=100, textvariable=self.start_season_var, width=8, command=self._update_preview, foreground="#000000")
        start_season_spin.grid(row=2, column=1, sticky="w", padx=4, pady=(6, 2))
        start_season_spin.bind("<KeyRelease>", self._update_preview)

        ttk.Label(se_frame, text="Start Episode (Un-tagged fallback):").grid(row=2, column=2, sticky="w", pady=(6, 2))
        self.start_ep_var = tk.StringVar(value="1")
        start_ep_spin = ttk.Spinbox(se_frame, from_=1, to=999, textvariable=self.start_ep_var, width=8, command=self._update_preview, foreground="#000000")
        start_ep_spin.grid(row=2, column=3, sticky="w", padx=4, pady=(6, 2))
        start_ep_spin.bind("<KeyRelease>", self._update_preview)

        preview_frame = ttk.LabelFrame(main_frame, text=" Live Canonical TVDB v4 English Season-Structured Preview ", padding=6)
        preview_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        main_frame.rowconfigure(4, weight=1)

        cols = ("orig", "season_folder", "new")
        self.tree = ttk.Treeview(preview_frame, columns=cols, show="headings")
        self.tree.heading("orig", text="Original Filename / Queue Order")
        self.tree.heading("season_folder", text="Season Folder")
        self.tree.heading("new", text="TheTVDB English Canonical Formatted Preview")
        self.tree.column("orig", width=280, anchor="w")
        self.tree.column("season_folder", width=110, anchor="center")
        self.tree.column("new", width=410, anchor="w")

        scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_box = ttk.Frame(main_frame)
        btn_box.grid(row=5, column=0, columnspan=3, sticky="e")

        ttk.Button(btn_box, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="📄 Export Preview Log", command=self._export_preview_log).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="💾 Save Settings", command=self._save_dialog_settings).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="Apply Names to Queue", style="Accent.TButton", command=self._apply_queue).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="⚡ Rename & Organize on Disk", style="Accent.TButton", command=self._apply_disk_now).pack(side=tk.RIGHT)

        self._update_preview()

    def _paste_apikey(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.apikey_entry.delete(0, tk.END)
                self.apikey_entry.insert(0, clipboard_text.strip())
        except Exception:
            pass

    def _paste_query(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                if self.query_entry.get() == self.query_entry.placeholder:
                    self.query_entry.delete(0, tk.END)
                    self.query_entry.configure(foreground=self.query_entry.default_fg)
                self.query_entry.delete(0, tk.END)
                self.query_entry.insert(0, clipboard_text.strip())
                self._update_preview()
        except Exception:
            pass

    def _export_preview_log(self):
        if not self.preview_map:
            messagebox.showwarning("No Preview", "No preview data available to export.", parent=self)
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Preview Log",
            parent=self
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== Greedy Media Utility TVDB v4 English Renamer Preview Log ===\n")
                    f.write(f"Query / Show: {self.query_entry.get_query()}\n")
                    f.write(f"Resolved Show Name: {self.resolved_show_name}\n")
                    f.write("-" * 60 + "\n\n")
                    for item in self.preview_map:
                        f.write(f"Original Path : {item['path']}\n")
                        f.write(f"Season Folder : {item.get('season_folder', 'N/A')}\n")
                        f.write(f"Proposed Name : {item['new_name']}\n")
                        f.write(f"Skipped (Special): {item.get('is_skipped', False)}\n")
                        f.write("-" * 40 + "\n")
                messagebox.showinfo("Export Successful", f"Preview log successfully saved to:\n{file_path}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save file: {e}", parent=self)

    def _fetch_tvdb_metadata(self):
        query = self.query_entry.get_query()
        api_key = self.apikey_entry.get().strip()

        if not api_key:
            messagebox.showwarning("API Key Required", "Please enter your free TheTVDB API v4 key to query official TVDB metadata.", parent=self)
            return
        if not query:
            messagebox.showwarning("Input Missing", "Please enter a show name or TVDB ID first.", parent=self)
            return

        self.status_lbl.config(text=f"Status: Authenticating & querying English TVDB v4...", foreground="#ff8080")
        self.update_idletasks()
        threading.Thread(target=self._fetch_tvdb_v4_worker, args=(api_key, query), daemon=True).start()

    def _fetch_tvdb_v4_worker(self, api_key, query):
        try:
            login_url = "https://api4.thetvdb.com/v4/login"
            login_data = json.dumps({"apikey": api_key}).encode("utf-8")
            req_login = urllib.request.Request(
                login_url, 
                data=login_data, 
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req_login, timeout=10) as resp:
                login_res = json.loads(resp.read().decode("utf-8"))
                token = login_res.get("data", {}).get("token")
                if not token:
                    raise Exception("Authentication token missing from response.")

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Accept-Language": "en"
            }

            series_id = None
            show_name = "Series"
            clean_q = query.strip()

            if clean_q.isdigit():
                series_id = clean_q
            else:
                encoded_q = urllib.parse.quote(query)
                search_url = f"https://api4.thetvdb.com/v4/search?q={encoded_q}&type=series"
                req_search = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req_search, timeout=10) as search_resp:
                    search_json = json.loads(search_resp.read().decode("utf-8"))
                    search_data = search_json.get("data", [])
                    if not search_data:
                        self.after(0, lambda: self.status_lbl.config(text="Status: Series not found on TheTVDB.", foreground="#ff1a40"))
                        return
                    best = search_data[0]
                    series_id = best.get("tvdb_id") or best.get("id")

            try:
                trans_url = f"https://api4.thetvdb.com/v4/series/{series_id}/translations/eng"
                req_trans = urllib.request.Request(trans_url, headers=headers)
                with urllib.request.urlopen(req_trans, timeout=10) as trans_resp:
                    trans_data = json.loads(trans_resp.read().decode("utf-8")).get("data", {})
                    if trans_data and trans_data.get("name"):
                        show_name = trans_data.get("name")
            except Exception:
                info_url = f"https://api4.thetvdb.com/v4/series/{series_id}"
                req_info = urllib.request.Request(info_url, headers=headers)
                with urllib.request.urlopen(req_info, timeout=10) as info_resp:
                    info_data = json.loads(info_resp.read().decode("utf-8"))
                    show_name = info_data.get("data", {}).get("name", "Series")

            self.resolved_show_name = show_name

            self.fetched_episodes_list = []
            page = 0
            while True:
                ep_url = f"https://api4.thetvdb.com/v4/series/{series_id}/episodes/default/eng?page={page}"
                req_eps = urllib.request.Request(ep_url, headers=headers)
                try:
                    with urllib.request.urlopen(req_eps, timeout=15) as ep_resp:
                        ep_json = json.loads(ep_resp.read().decode("utf-8"))
                        data_obj = ep_json.get("data", {})
                        ep_data = data_obj.get("episodes", [])
                        if not ep_data:
                            break

                        for ep in ep_data:
                            season = ep.get("seasonNumber", 1)
                            number = ep.get("number", 1)
                            title = ep.get("name", "")
                            
                            if season == 0:
                                continue

                            self.fetched_episodes_list.append({
                                "season": season,
                                "number": number,
                                "title": title if title else f"Episode {number}"
                            })

                        if len(ep_data) < 50:
                            break
                        page += 1
                        if page > 50:
                            break
                except Exception:
                    if page == 0:
                        ep_url_fb = f"https://api4.thetvdb.com/v4/series/{series_id}/episodes/default"
                        req_fb = urllib.request.Request(ep_url_fb, headers=headers)
                        with urllib.request.urlopen(req_fb, timeout=15) as fb_resp:
                            fb_json = json.loads(fb_resp.read().decode("utf-8"))
                            fb_data = fb_json.get("data", {}).get("episodes", [])
                            for ep in fb_data:
                                season = ep.get("seasonNumber", 1)
                                number = ep.get("number", 1)
                                title = ep.get("name", "")
                                if season == 0:
                                    continue
                                self.fetched_episodes_list.append({
                                    "season": season, "number": number,
                                    "title": title if title else f"Episode {number}"
                                })
                    break

            self.after(0, lambda: self.status_lbl.config(text=f"Status: Loaded '{show_name}' ({len(self.fetched_episodes_list)} English canonical episodes) ✅", foreground="#ff4d4d"))
            self.after(0, self._update_preview)
        except Exception as e:
            self.after(0, lambda: self.status_lbl.config(text=f"Status: TVDB API Error ({e}).", foreground="#ff1a40"))

    def _parse_filename_for_se(self, filename):
        se_match = re.search(r'[sS](\d+)[eE](\d+)', filename)
        if se_match:
            return int(se_match.group(1)), int(se_match.group(2))
        return None, None

    def _update_preview(self, *args):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        self.tree.delete(*self.tree.get_children())
        
        raw_show_prefix = self.resolved_show_name if self.resolved_show_name else self.query_entry.get_query()
        if not raw_show_prefix or raw_show_prefix.isdigit() or len(raw_show_prefix) <= 2:
            raw_show_prefix = "Show"
        
        clean_show_prefix = re.sub(r'[\\/*?:"<>|]', "", raw_show_prefix)
        series_prefix = f"{clean_show_prefix} "
        
        use_3_digits = "3 Digits" in self.padding_var.get()
        separator = self.sep_var.get()
        include_title = self.include_title_var.get()

        try:
            target_start_season = int(self.start_season_var.get())
        except ValueError:
            target_start_season = 1

        try:
            target_start_ep = int(self.start_ep_var.get())
        except ValueError:
            target_start_ep = 1

        start_list_idx = 0
        if self.fetched_episodes_list:
            for i, ep in enumerate(self.fetched_episodes_list):
                if ep["season"] == target_start_season and ep["number"] == target_start_ep:
                    start_list_idx = i
                    break

        self.preview_map = []
        for idx, item in enumerate(self.items_data):
            orig = item["name"]
            _, ext = os.path.splitext(orig)
            ext = ext.lower()

            season_num = target_start_season
            ep_num = target_start_ep + idx
            raw_title = f"Episode {ep_num}"

            parsed_s, parsed_e = self._parse_filename_for_se(orig)
            if parsed_s is not None and parsed_e is not None:
                if parsed_s == 0:
                    season_folder = "SKIPPED (Special)"
                    new_name = orig
                    self.preview_map.append({
                        "item_id": item["item_id"], "path": item["path"], 
                        "new_name": new_name, "season_folder": season_folder, "is_skipped": True
                    })
                    self.tree.insert("", tk.END, values=(orig, season_folder, new_name))
                    continue
                else:
                    season_num = parsed_s
                    ep_num = parsed_e
                    match_ep = next((ep for ep in self.fetched_episodes_list if ep["season"] == season_num and ep["number"] == ep_num), None)
                    if match_ep:
                        raw_title = match_ep["title"]
            else:
                mapped_idx = start_list_idx + idx
                if mapped_idx < len(self.fetched_episodes_list):
                    season_num = self.fetched_episodes_list[mapped_idx]["season"]
                    ep_num = self.fetched_episodes_list[mapped_idx]["number"]
                    raw_title = self.fetched_episodes_list[mapped_idx]["title"]

            season_folder = f"Season {season_num:02d}"
            season_str = f"S{season_num:02d}"
            ep_str = f"E{ep_num:03d}" if use_3_digits else f"E{ep_num:02d}"
            se_tag = f"{season_str}{ep_str}"

            title_tag = ""
            if include_title:
                clean_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)
                title_tag = f"{separator}{clean_title}"

            new_name = f"{series_prefix}{se_tag}{title_tag}{ext}"
            self.preview_map.append({
                "item_id": item["item_id"], 
                "path": item["path"], 
                "new_name": new_name,
                "season_folder": season_folder,
                "is_skipped": False
            })
            self.tree.insert("", tk.END, values=(orig, season_folder, new_name))

    def _apply_queue(self):
        self._save_dialog_settings()
        self.rename_disk_immediately = False
        self.result = self.preview_map
        self.destroy()

    def _apply_disk_now(self):
        if messagebox.askyesno("Confirm", "Rename files and sort into TheTVDB English canonical season folders on disk?", parent=self):
            self._save_dialog_settings()
            self.rename_disk_immediately = True
            self.result = self.preview_map
            self.destroy()


class TrackInspectorDialog(tk.Toplevel):
    def __init__(self, parent, file_path, streams_data, current_theme):
        super().__init__(parent)
        self.title(f"Track Inspector - {os.path.basename(file_path)}")
        self.geometry("680x420")
        self.theme = current_theme
        self.configure(bg=self.theme["bg"])
        self.file_path = file_path
        self.streams_data = streams_data
        self.excluded_tracks = []

        self._build_ui()
        self.transient(parent)
        self.grab_set()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text=f"Stream Tracks: {os.path.basename(self.file_path)}",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 4))

        cols = ("idx", "type", "codec", "lang", "title", "action")
        self.tree = ttk.Treeview(main_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("idx", text="Stream #")
        self.tree.heading("type", text="Type")
        self.tree.heading("codec", text="Codec")
        self.tree.heading("lang", text="Lang")
        self.tree.heading("title", text="Title")
        self.tree.heading("action", text="State")

        self.tree.column("idx", width=60, anchor="center")
        self.tree.column("type", width=70, anchor="center")
        self.tree.column("codec", width=80, anchor="center")
        self.tree.column("lang", width=70, anchor="center")
        self.tree.column("title", width=200, anchor="w")
        self.tree.column("action", width=110, anchor="center")

        scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._populate_tracks()

        btn_box = ttk.Frame(main_frame)
        btn_box.pack(fill=tk.X, pady=(6, 0))

        remove_btn = ttk.Button(btn_box, text="❌ Toggle Track Removal", command=self._toggle_exclude)
        remove_btn.pack(side=tk.LEFT)

        apply_btn = ttk.Button(btn_box, text="Apply Exclusions", style="Accent.TButton", command=self._apply)
        apply_btn.pack(side=tk.RIGHT)

    def _populate_tracks(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.streams_data:
            idx = s.get("index")
            stype = s.get("codec_type", "unknown").upper()
            codec = s.get("codec_name", "")
            tags = s.get("tags", {})
            lang = tags.get("language", "und/unnamed")
            title = tags.get("title", "No Title")
            state = "❌ REMOVED" if idx in self.excluded_tracks else "Keep Track"

            self.tree.insert("", tk.END, values=(idx, stype, codec, lang, title, state))

    def _toggle_exclude(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Track", "Select a track from the list to remove.")
            return

        item = self.tree.item(selected[0])
        track_idx = int(item["values"][0])

        if track_idx in self.excluded_tracks:
            self.excluded_tracks.remove(track_idx)
        else:
            self.excluded_tracks.append(track_idx)

        self._populate_tracks()

    def _apply(self):
        self.destroy()


class GreedyMediaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Greedy Media Utility")
        self.geometry("980x800")
        self.minsize(860, 680)

        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GreedyMediaUtility")
        os.makedirs(self.user_data_dir, exist_ok=True)

        self.logs_dir = os.path.join(self.user_data_dir, "logs")
        self.config_path = os.path.join(self.user_data_dir, "settings.json")
        os.makedirs(self.logs_dir, exist_ok=True)

        session_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_log_path = os.path.join(self.logs_dir, f"greedymedia_session_{session_time}.log")

        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_path = shutil.which("ffprobe") or "ffprobe"

        self.current_theme_name = "Greedy Occult"  # Default theme matching artwork
        self.task_queue = queue.Queue()
        self.is_processing = False
        self.stop_requested = False
        self.current_proc = None
        self.custom_input_dir = ""
        self.custom_output_dir = ""
        self.manual_excluded_streams = {}
        self.advanced_visible = False
        
        self.rename_undo_history = []
        self.logo_photo = None
        self.logo_lbl = None

        self.renamer_settings = {
            "query": "One Piece",
            "tvdb_api_key": "",
            "padding": "2 Digits (E01, E02)",
            "separator": " - ",
            "include_title": True,
            "start_season": "1",
            "start_ep": "1"
        }

        self._build_ui()
        self._init_styles()
        self._load_settings()

        self.log("⚡ Greedy Media Utility initialized.")
        self.log(f"📁 Log session saved to: {self.session_log_path}")

        # Trigger startup flashing animation for the golden donate button
        self.after(500, lambda: self._flash_donate_button(6))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        
        # Golden Yellow Donate Button Style
        self.style.configure(
            "FancyDonate.TButton", 
            background="#FFD700", 
            foreground="#12090b", 
            font=("Segoe UI", 10, "bold"), 
            padding=6
        )
        self.style.map("FancyDonate.TButton", background=[("active", "#FFEE58")])

        self.apply_theme(self.current_theme_name)

    def _flash_donate_button(self, count=6):
        """Creates a smooth pulsing/flashing effect on startup for the donate button."""
        if count <= 0:
            self.style.configure("FancyDonate.TButton", background="#FFD700")
            return
        
        current_bg = self.style.lookup("FancyDonate.TButton", "background")
        next_bg = "#FFA500" if current_bg == "#FFD700" else "#FFD700"
        self.style.configure("FancyDonate.TButton", background=next_bg)
        
        self.after(350, lambda: self._flash_donate_button(count - 1))

    def apply_theme(self, theme_name):
        self.current_theme_name = theme_name
        t = THEMES[theme_name]

        self.configure(bg=t["bg"])

        self.style.configure(".", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 9, "bold"))
        self.style.configure("TFrame", background=t["bg"])
        self.style.configure("TLabelframe", background=t["card_bg"], foreground=t["accent"], font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe.Label", background=t["card_bg"], foreground=t["accent"])

        self.style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        self.style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])

        self.style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000", font=("Segoe UI", 9, "bold"))
        self.style.configure("TSpinbox", fieldbackground="#ffffff", foreground="#000000", font=("Segoe UI", 9, "bold"))
        self.style.configure("TCombobox", fieldbackground="#ffffff", background=t["btn_bg"], foreground="#000000", selectbackground=t["highlight"], selectforeground="#ffffff")
        self.style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")], foreground=[("readonly", "#000000")])

        self.style.configure("TButton", background=t["btn_bg"], foreground=t["btn_fg"], borderwidth=1, bordercolor=t["accent"], padding=4)
        self.style.map("TButton", background=[("active", t["highlight"])])
        self.style.configure("Accent.TButton", background=t["accent"], foreground="#ffffff" if theme_name == "macOS Light" else "#12090b", font=("Segoe UI", 9, "bold"))
        self.style.configure("Stop.TButton", background="#ff1a40", foreground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.style.configure("Preview.TButton", background="#ff8080" if "Greedy" in theme_name or "Dark" in theme_name else "#ff9f1c", foreground="#12090b", font=("Segoe UI", 9, "bold"))

        self.style.configure("Treeview", background=t["card_bg"], foreground=t["fg"], fieldbackground=t["card_bg"], rowheight=22)
        self.style.configure("Treeview.Heading", background=t["btn_bg"], foreground=t["fg"], font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", t["highlight"])], foreground=[("selected", t["fg"])])

        if hasattr(self, "log_text") and self.log_text.winfo_exists():
            self.log_text.config(bg=t["log_bg"], fg=t["fg"])

        if hasattr(self, "logo_lbl") and self.logo_lbl and self.logo_lbl.winfo_exists():
            self.logo_lbl.config(bg=t["bg"])

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 6))

        t = THEMES[self.current_theme_name]

        # Load and set icon.jpeg using resource_path for reliable bundling
        if PIL_AVAILABLE:
            logo_path = resource_path("icon.jpeg")
            if os.path.exists(logo_path):
                try:
                    pil_img = Image.open(logo_path)
                    
                    # Window border icon
                    icon_img = ImageTk.PhotoImage(pil_img.resize((64, 64), Image.Resampling.LANCZOS))
                    self.iconphoto(True, icon_img)
                    self._app_icon = icon_img  # Prevent garbage collection

                    # Header GUI image
                    header_img = ImageTk.PhotoImage(pil_img.resize((36, 36), Image.Resampling.LANCZOS))
                    self.logo_photo = header_img
                    self.logo_lbl = tk.Label(header_frame, image=self.logo_photo, bg=t["bg"])
                    self.logo_lbl.pack(side=tk.LEFT, padx=(0, 6))
                except Exception as e:
                    print(f"Error loading icon image: {e}")

        header = tk.Label(
            header_frame, 
            text="⚡ Greedy Media Utility", 
            font=("Segoe UI", 16, "bold"), 
            bg=t["bg"], 
            fg="#ff4d4d"
        )
        header.pack(side=tk.LEFT)

        header_right_frame = ttk.Frame(header_frame)
        header_right_frame.pack(side=tk.RIGHT)

        donate_btn = ttk.Button(header_right_frame, text="💖 Donate & Support", style="FancyDonate.TButton", command=self.open_donate_link)
        donate_btn.pack(side=tk.LEFT, padx=(0, 8))

        save_cfg_btn = ttk.Button(header_right_frame, text="💾 Save Settings", command=self.save_settings)
        save_cfg_btn.pack(side=tk.LEFT, padx=(0, 6))

        theme_btn = ttk.Button(header_right_frame, text="⚙️ Themes", command=self._open_theme_menu)
        theme_btn.pack(side=tk.LEFT)

        config_frame = ttk.LabelFrame(main_frame, text=" Folders & Transcode Configuration ", padding=8)
        config_frame.pack(fill=tk.X, pady=(0, 6))
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="📁 Source Folder / Files:").grid(row=0, column=0, sticky="w", pady=2)
        self.in_dir_var = tk.StringVar(value="[No folder/files loaded - Click Browse or Add Files]")
        in_entry = ttk.Entry(config_frame, textvariable=self.in_dir_var, state="readonly", foreground="#000000")
        in_entry.grid(row=0, column=1, sticky="ew", padx=(8, 4), pady=2)
        
        in_btn_frame = ttk.Frame(config_frame)
        in_btn_frame.grid(row=0, column=2, sticky="e", pady=2)
        
        browse_in_btn = ttk.Button(in_btn_frame, text="Browse Folder...", command=self._select_input_dir)
        browse_in_btn.pack(side=tk.LEFT, padx=(0, 4))

        browse_files_btn = ttk.Button(in_btn_frame, text="Add Files...", command=self._select_individual_files)
        browse_files_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        refresh_folder_btn = ttk.Button(in_btn_frame, text="🔄 Refresh", command=self.refresh_source_folder)
        refresh_folder_btn.pack(side=tk.LEFT)

        ttk.Label(config_frame, text="💾 Output Directory:").grid(row=1, column=0, sticky="w", pady=2)
        self.out_dir_var = tk.StringVar(value="[Auto: 'compressed/' inside source folder]")
        out_entry = ttk.Entry(config_frame, textvariable=self.out_dir_var, state="readonly", foreground="#000000")
        out_entry.grid(row=1, column=1, sticky="ew", padx=(8, 4), pady=2)
        
        out_btn_frame = ttk.Frame(config_frame)
        out_btn_frame.grid(row=1, column=2, sticky="e", pady=2)
        browse_out_btn = ttk.Button(out_btn_frame, text="Browse Output...", command=self._select_output_dir)
        browse_out_btn.pack(side=tk.LEFT, padx=(0, 4))
        open_out_btn = ttk.Button(out_btn_frame, text="📂 Open Output", command=self.open_output_folder)
        open_out_btn.pack(side=tk.LEFT)

        self.recursive_scan_var = tk.BooleanVar(value=True)
        recursive_chk = ttk.Checkbutton(config_frame, text="Scan folder and all subfolders/season directories recursively", variable=self.recursive_scan_var)
        recursive_chk.grid(row=2, column=0, columnspan=3, sticky="w", padx=(0, 0), pady=(4, 2))

        ttk.Label(config_frame, text="Duplicate Handling:").grid(row=3, column=0, sticky="w", pady=2)
        self.collision_var = tk.StringVar(value="Skip if Output Exists (Safe Resume)")
        collision_options = [
            "Skip if Output Exists (Safe Resume)",
            "Overwrite Output File",
            "Prompt / Ask Me"
        ]
        collision_cb = ttk.Combobox(config_frame, textvariable=self.collision_var, values=collision_options, state="readonly")
        collision_cb.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=2)

        self.toggle_adv_btn = ttk.Button(config_frame, text="▶ Show Advanced Transcode & Track Settings", command=self._toggle_advanced_settings)
        self.toggle_adv_btn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 2))

        self.adv_frame = ttk.Frame(config_frame)
        self.adv_frame.columnconfigure(1, weight=1)

        ttk.Label(self.adv_frame, text="Encoder Engine:").grid(row=0, column=0, sticky="w", pady=2)
        self.encoder_var = tk.StringVar(value="av1_nvenc 10-bit (Nvidia Hardware)")
        encoders = [
            "av1_nvenc 10-bit (Nvidia Hardware)",
            "hevc_nvenc 10-bit (Nvidia H.265)",
            "av1_qsv 10-bit (Intel Hardware)",
            "libsvtav1 10-bit (CPU Software - Slower/Smaller)"
        ]
        encoder_cb = ttk.Combobox(self.adv_frame, textvariable=self.encoder_var, values=encoders, state="readonly")
        encoder_cb.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=2)

        ttk.Label(self.adv_frame, text="Compression Strategy:").grid(row=1, column=0, sticky="w", pady=2)
        self.strategy_var = tk.StringVar(value="Target File Size")
        strategy_cb = ttk.Combobox(self.adv_frame, textvariable=self.strategy_var, values=["Target File Size", "Constant Quality (CQ/RF)"], state="readonly")
        strategy_cb.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=2)
        strategy_cb.bind("<<ComboboxSelected>>", self._toggle_strategy_inputs)

        self.size_label = ttk.Label(self.adv_frame, text="Target Size (MB):")
        self.size_label.grid(row=2, column=0, sticky="w", pady=2)
        
        size_frame = ttk.Frame(self.adv_frame)
        size_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=2)
        
        self.target_size_var = tk.StringVar(value="55")
        self.size_spin = ttk.Spinbox(size_frame, from_=0, to=999, textvariable=self.target_size_var, width=6, command=self._update_estimate_preview, foreground="#000000")
        self.size_spin.pack(side=tk.LEFT)
        self.size_spin.bind("<KeyRelease>", self._update_estimate_preview)

        mini_hq_btn = ttk.Button(size_frame, text="⭐ Mini HQ Mode", command=lambda: [
            self.strategy_var.set("Constant Quality (CQ/RF)"),
            self._toggle_strategy_inputs(),
            self.target_size_var.set("55"),
            self._update_estimate_preview()
        ])
        mini_hq_btn.pack(side=tk.LEFT, padx=(6, 0))

        self.estimate_label = ttk.Label(size_frame, text=" 📊 Video Bitrate: ~250 kbps")
        self.estimate_label.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(self.adv_frame, text="Custom Output Suffix Tag:").grid(row=3, column=0, sticky="w", pady=2)
        self.custom_suffix_var = tk.StringVar(value="")
        custom_suffix_entry = ttk.Entry(self.adv_frame, textvariable=self.custom_suffix_var, foreground="#000000")
        custom_suffix_entry.grid(row=3, column=1, sticky="ew", padx=6, pady=2)
        ttk.Label(self.adv_frame, text="(e.g. _customtag)").grid(row=3, column=2, sticky="w", pady=2)

        ttk.Label(self.adv_frame, text="Aspect Ratio / Res:").grid(row=4, column=0, sticky="w", pady=2)
        self.aspect_var = tk.StringVar(value="Same as Source")
        aspect_options = [
            "Same as Source",
            "16:9 (1920x1080 - 1080p)",
            "16:9 (1280x720 - 720p)",
            "16:9 (854x480 - 480p)",
            "16:9 (640x360 - 360p)",
            "4:3 (1440x1080)",
            "21:9 (2560x1080)"
        ]
        aspect_cb = ttk.Combobox(self.adv_frame, textvariable=self.aspect_var, values=aspect_options, state="readonly")
        aspect_cb.grid(row=4, column=1, columnspan=2, sticky="ew", padx=6, pady=2)

        ttk.Label(self.adv_frame, text="Audio Encoding Mode:").grid(row=5, column=0, sticky="w", pady=2)
        self.audio_var = tk.StringVar(value="Opus Stereo @ 48 kbps (Ultra-Slim)")
        audio_options = ["Opus Stereo @ 48 kbps (Ultra-Slim)", "AAC Stereo @ 96 kbps", "Copy Original Audio", "❌ Remove All Audio (Mute Stream)"]
        audio_cb = ttk.Combobox(self.adv_frame, textvariable=self.audio_var, values=audio_options, state="readonly")
        audio_cb.grid(row=5, column=1, columnspan=2, sticky="ew", padx=6, pady=2)

        ttk.Label(self.adv_frame, text="Subtitle Handling:").grid(row=6, column=0, sticky="w", pady=2)
        self.sub_var = tk.StringVar(value="Copy All Subtitle Tracks")
        sub_options = ["Copy All Subtitle Tracks", "❌ Strip All Subtitles"]
        sub_cb = ttk.Combobox(self.adv_frame, textvariable=self.sub_var, values=sub_options, state="readonly")
        sub_cb.grid(row=6, column=1, columnspan=2, sticky="ew", padx=6, pady=2)

        ttk.Label(self.adv_frame, text="Remove Specific Audio Track:").grid(row=7, column=0, sticky="w", pady=2)
        self.audio_track_remove_var = tk.StringVar(value="None (Keep All Audio Tracks)")
        audio_track_options = [
            "None (Keep All Audio Tracks)",
            "❌ Remove Audio Track 1 (a:0)",
            "❌ Remove Audio Track 2 (a:1)",
            "❌ Remove Audio Track 3 (a:2)",
            "❌ Remove Audio Track 4 (a:3)",
            "❌ Remove Audio Track 5 (a:4)"
        ]
        audio_track_cb = ttk.Combobox(self.adv_frame, textvariable=self.audio_track_remove_var, values=audio_track_options, state="readonly")
        audio_track_cb.grid(row=7, column=1, columnspan=2, sticky="ew", padx=6, pady=2)

        ttk.Label(self.adv_frame, text="Remove Subtitle Tracks:").grid(row=8, column=0, sticky="w", pady=2)
        self.sub_track_remove_var = tk.StringVar(value="")
        sub_tr_entry = ttk.Entry(self.adv_frame, textvariable=self.sub_track_remove_var, foreground="#000000")
        sub_tr_entry.grid(row=8, column=1, sticky="ew", padx=6, pady=2)
        ttk.Label(self.adv_frame, text="(e.g. 0, 1)").grid(row=8, column=2, sticky="w", pady=2)

        opt_sub_frame = ttk.Frame(main_frame)
        opt_sub_frame.pack(fill=tk.X, pady=(0, 4))

        self.sound_notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_sub_frame, text="🔊 Play Sound when Complete", variable=self.sound_notify_var).pack(side=tk.LEFT, padx=(0, 10))

        self.auto_shutdown_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_sub_frame, text="🌙 Auto-Shutdown PC", variable=self.auto_shutdown_var).pack(side=tk.LEFT)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 6))

        left_actions = ttk.Frame(btn_frame)
        left_actions.pack(side=tk.LEFT)

        right_actions = ttk.Frame(btn_frame)
        right_actions.pack(side=tk.RIGHT)

        inspect_btn = ttk.Button(left_actions, text="🔍 Inspect Tracks", command=self.inspect_tracks)
        inspect_btn.pack(side=tk.LEFT, padx=(0, 4))

        preview_btn = ttk.Button(left_actions, text="🎬 3-Min Preview", style="Preview.TButton", command=self.start_preview)
        preview_btn.pack(side=tk.LEFT, padx=(0, 4))

        rename_tool_btn = ttk.Button(left_actions, text="🛠️ Bulk Rename & Folders", style="Accent.TButton", command=self._open_rename_folder_tool_menu)
        rename_tool_btn.pack(side=tk.LEFT, padx=(0, 4))

        clear_btn = ttk.Button(left_actions, text="Clear Queue", command=self.clear_queue)
        clear_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.stop_btn = ttk.Button(right_actions, text="STOP", style="Stop.TButton", command=self.stop_encoding, state="disabled")
        self.stop_btn.pack(side=tk.RIGHT, padx=(0, 0))

        self.start_btn = ttk.Button(right_actions, text="▶ START", style="Accent.TButton", command=self.start_batch)
        self.start_btn.pack(side=tk.RIGHT, padx=(4, 4))

        self.single_btn = ttk.Button(right_actions, text="▶ Encode Selected", command=self.start_single)
        self.single_btn.pack(side=tk.RIGHT, padx=(0, 4))

        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        columns = ("file", "duration", "estimated", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("file", text="Video File")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("estimated", text="Target Size")
        self.tree.heading("status", text="Status / Progress")
        
        self.tree.column("file", width=300, anchor="w")
        self.tree.column("duration", width=70, anchor="center")
        self.tree.column("estimated", width=90, anchor="center")
        self.tree.column("status", width=200, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Delete>", lambda e: self.remove_selected_item())

        log_header_frame = ttk.Frame(main_frame)
        log_header_frame.pack(fill=tk.X)

        ttk.Label(log_header_frame, text=" Real-time Output Log ").pack(side=tk.LEFT)
        open_log_btn = ttk.Button(log_header_frame, text="📜 Open Logs Folder", command=self.open_logs_folder)
        open_log_btn.pack(side=tk.RIGHT, pady=(0, 2))

        log_frame = ttk.LabelFrame(main_frame, text="", padding=4)
        log_frame.pack(fill=tk.X)

        self.log_text = tk.Text(log_frame, height=4, bg="#090305", fg="#ff4d4d", font=("Consolas", 8, "bold"), relief="flat")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def open_donate_link(self):
        webbrowser.open("https://www.paypal.com/donate/?hosted_button_id=LUT2LHRKQ27LN")
        self.log("💖 Opened PayPal donation link in browser.")

    def _open_rename_folder_tool_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="🌐 Smart TVDB Renamer", command=self.open_online_rename)
        menu.add_command(label="🛠️ Bulk Rename & Folder Creator Suite", command=self.open_bulk_rename_folder_suite)
        menu.add_separator()
        
        undo_state = "normal" if self.rename_undo_history else "disabled"
        menu.add_command(label="🔄 Undo Last Disk Rename", command=self.undo_last_rename, state=undo_state)

        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def save_settings(self):
        queue_items = []
        for task in list(self.task_queue.queue):
            queue_items.append({
                "path": task["path"],
                "custom_name": task.get("custom_name", os.path.basename(task["path"]))
            })

        config = {
            "custom_input_dir": self.custom_input_dir,
            "custom_output_dir": self.custom_output_dir,
            "recursive_scan": self.recursive_scan_var.get(),
            "collision_mode": self.collision_var.get(),
            "encoder": self.encoder_var.get(),
            "strategy": self.strategy_var.get(),
            "target_size": self.target_size_var.get(),
            "custom_suffix": self.custom_suffix_var.get(),
            "aspect": self.aspect_var.get(),
            "audio": self.audio_var.get(),
            "sub": self.sub_var.get(),
            "audio_remove": self.audio_track_remove_var.get(),
            "sub_remove": self.sub_track_remove_var.get(),
            "sound_notify": self.sound_notify_var.get(),
            "auto_shutdown": self.auto_shutdown_var.get(),
            "theme": self.current_theme_name,
            "renamer_settings": self.renamer_settings,
            "queue_items": queue_items
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            self.log("💾 Settings and queue state successfully saved.")
            messagebox.showinfo("Saved", "Settings and queue state successfully saved!")
        except Exception as e:
            self.log(f"❌ Failed to save settings: {e}")

    def _load_settings(self):
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.custom_input_dir = config.get("custom_input_dir", "")
            if self.custom_input_dir and os.path.exists(self.custom_input_dir):
                self.in_dir_var.set(self.custom_input_dir)

            self.custom_output_dir = config.get("custom_output_dir", "")
            if self.custom_output_dir:
                self.out_dir_var.set(self.custom_output_dir)
            elif self.custom_input_dir:
                self.out_dir_var.set(os.path.join(self.custom_input_dir, "compressed"))

            if "recursive_scan" in config:
                self.recursive_scan_var.set(config["recursive_scan"])
            if "collision_mode" in config:
                self.collision_var.set(config["collision_mode"])
            if "encoder" in config:
                self.encoder_var.set(config["encoder"])
            if "strategy" in config:
                self.strategy_var.set(config["strategy"])
            if "target_size" in config:
                self.target_size_var.set(config["target_size"])
            if "custom_suffix" in config:
                self.custom_suffix_var.set(config["custom_suffix"])
            if "aspect" in config:
                self.aspect_var.set(config["aspect"])
            if "audio" in config:
                self.audio_var.set(config["audio"])
            if "sub" in config:
                self.sub_var.set(config["sub"])
            if "audio_remove" in config:
                self.audio_track_remove_var.set(config["audio_remove"])
            if "sub_remove" in config:
                self.sub_track_remove_var.set(config["sub_remove"])
            if "sound_notify" in config:
                self.sound_notify_var.set(config["sound_notify"])
            if "auto_shutdown" in config:
                self.auto_shutdown_var.set(config["auto_shutdown"])
            if "theme" in config and config["theme"] in THEMES:
                self.apply_theme(config["theme"])
            if "renamer_settings" in config:
                self.renamer_settings.update(config["renamer_settings"])

            saved_queue = config.get("queue_items", [])
            if saved_queue:
                for item in saved_queue:
                    f_path = item["path"]
                    if os.path.exists(f_path):
                        base_name = item.get("custom_name", os.path.basename(f_path))
                        est_size_str = f"~{self.target_size_var.get()} MB" if self.strategy_var.get() == "Target File Size" else "CQ Mode"
                        item_id = self.tree.insert("", tk.END, values=(base_name, "Loading...", est_size_str, "Queued"))
                        self.task_queue.put({
                            "item_id": item_id,
                            "path": f_path,
                            "duration": 1440.0,
                            "custom_name": base_name
                        })
                self.log(f"📥 Restored {len(saved_queue)} item(s) from previous session queue.")
                
                def background_probe():
                    temp_tasks = list(self.task_queue.queue)
                    for task in temp_tasks:
                        f_path = task["path"]
                        item_id = task["item_id"]
                        duration_str, duration_sec = self._get_video_duration(f_path)
                        task["duration"] = duration_sec
                        try:
                            current_vals = self.tree.item(item_id, "values")
                            if current_vals:
                                self.after(0, lambda i=item_id, v0=current_vals[0], d=duration_str, v2=current_vals[2], v3=current_vals[3]: 
                                           self.tree.item(i, values=(v0, d, v2, v3)))
                        except Exception:
                            pass

                threading.Thread(target=background_probe, daemon=True).start()

            self.log("⚙️ Loaded previous settings.")
        except Exception as e:
            self.log(f"⚠️ Could not load settings: {e}")

    def _on_close(self):
        try:
            queue_items = []
            for task in list(self.task_queue.queue):
                queue_items.append({
                    "path": task["path"],
                    "custom_name": task.get("custom_name", os.path.basename(task["path"]))
                })

            config = {
                "custom_input_dir": self.custom_input_dir,
                "custom_output_dir": self.custom_output_dir,
                "recursive_scan": self.recursive_scan_var.get(),
                "collision_mode": self.collision_var.get(),
                "encoder": self.encoder_var.get(),
                "strategy": self.strategy_var.get(),
                "target_size": self.target_size_var.get(),
                "custom_suffix": self.custom_suffix_var.get(),
                "aspect": self.aspect_var.get(),
                "audio": self.audio_var.get(),
                "sub": self.sub_var.get(),
                "audio_remove": self.audio_track_remove_var.get(),
                "sub_remove": self.sub_track_remove_var.get(),
                "sound_notify": self.sound_notify_var.get(),
                "auto_shutdown": self.auto_shutdown_var.get(),
                "theme": self.current_theme_name,
                "renamer_settings": self.renamer_settings,
                "queue_items": queue_items
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
        self.destroy()

    def _toggle_advanced_settings(self):
        if self.advanced_visible:
            self.adv_frame.grid_forget()
            self.toggle_adv_btn.config(text="▶ Show Advanced Transcode & Track Settings")
            self.advanced_visible = False
        else:
            self.adv_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=4)
            self.toggle_adv_btn.config(text="▼ Hide Advanced Settings")
            self.advanced_visible = True

    def _get_filename_tags(self):
        encoder_selection = self.encoder_var.get()
        aspect_selection = self.aspect_var.get()
        custom_sfx = self.custom_suffix_var.get().strip()

        if "1920x1080" in aspect_selection:
            res_tag = "1080p"
        elif "1280x720" in aspect_selection:
            res_tag = "720p"
        elif "854x480" in aspect_selection:
            res_tag = "480p"
        elif "640x360" in aspect_selection:
            res_tag = "360p"
        elif "1440x1080" in aspect_selection:
            res_tag = "1440x1080"
        elif "2560x1080" in aspect_selection:
            res_tag = "2560x1080"
        else:
            res_tag = "src-res"

        if "av1_nvenc" in encoder_selection:
            codec_tag = "10bit-av1-nvenc"
        elif "hevc_nvenc" in encoder_selection:
            codec_tag = "10bit-hevc-nvenc"
        elif "av1_qsv" in encoder_selection:
            codec_tag = "10bit-av1-qsv"
        else:
            codec_tag = "10bit-svtav1"

        combined = f"_{res_tag}_{codec_tag}"
        if custom_sfx:
            if not custom_sfx.startswith("_"):
                custom_sfx = f"_{custom_sfx}"
            combined += custom_sfx
        return combined

    def refresh_source_folder(self):
        if self.is_processing:
            messagebox.showwarning("Busy", "Cannot refresh folder while encoding is in progress.")
            return

        if self.custom_input_dir and os.path.exists(self.custom_input_dir):
            self.log(f"🔄 Refreshing source folder: {self.custom_input_dir}")
            threading.Thread(target=self._load_files_from_folder_worker, args=(self.custom_input_dir,), daemon=True).start()
        else:
            messagebox.showinfo("No Folder Loaded", "Please select a valid source folder first.")

    def open_output_folder(self):
        target_dir = self.custom_output_dir if self.custom_output_dir else (os.path.join(self.custom_input_dir, "compressed") if self.custom_input_dir else "")

        if not target_dir or not os.path.exists(target_dir):
            if self.custom_input_dir and os.path.exists(self.custom_input_dir):
                target_dir = os.path.join(self.custom_input_dir, "compressed")
                os.makedirs(target_dir, exist_ok=True)
            else:
                messagebox.showinfo("Folder Not Found", "Please select a source folder or choose an output directory first.")
                return

        if sys.platform == "win32":
            os.startfile(target_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target_dir])
        else:
            subprocess.Popen(["xdg-open", target_dir])

        self.log(f"📂 Opened output directory: {target_dir}")

    def open_logs_folder(self):
        if os.path.exists(self.logs_dir):
            if sys.platform == "win32":
                os.startfile(self.logs_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.logs_dir])
            else:
                subprocess.Popen(["xdg-open", self.logs_dir])

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        formatted_msg = f"{timestamp}{message}"
        if hasattr(self, "log_text") and self.log_text.winfo_exists():
            self.log_text.insert(tk.END, f"{formatted_msg}\n")
            self.log_text.see(tk.END)

        try:
            with open(self.session_log_path, "a", encoding="utf-8") as f:
                f.write(f"{formatted_msg}\n")
        except Exception:
            pass

    def _open_theme_menu(self):
        menu = tk.Menu(self, tearoff=0)
        for theme_name in THEMES.keys():
            menu.add_command(label=theme_name, command=lambda name=theme_name: self._change_theme(name))
        menu.post(self.winfo_pointerx(), self.winfo_pointery())

    def _change_theme(self, theme_name):
        self.apply_theme(theme_name)
        self.log(f"🎨 Applied theme: {theme_name}")

    def _toggle_strategy_inputs(self, event=None):
        if self.strategy_var.get() == "Target File Size":
            self.size_label.config(text="Target Size (MB):")
            self.target_size_var.set("55")
        else:
            self.size_label.config(text="Constant Quality (CQ):")
            self.target_size_var.set("28")
        self._update_estimate_preview()

    def _update_estimate_preview(self, event=None):
        try:
            if self.strategy_var.get() == "Target File Size":
                target_mb = float(self.target_size_var.get())
                avg_duration = 1440.0
                
                audio_selection = self.audio_var.get()
                audio_kbps = 0 if "Remove" in audio_selection else (48 if "Opus" in audio_selection else 96)
                
                total_bitrate = (target_mb * 8192) / avg_duration
                video_bitrate = max(int(total_bitrate - audio_kbps), 100)
                
                self.estimate_label.config(text=f" 📊 Video Bitrate: ~{video_bitrate} kbps")
            else:
                cq = self.target_size_var.get()
                self.estimate_label.config(text=f" 📊 CQ Mode ({cq})")
        except ValueError:
            pass

    def _select_input_dir(self):
        chosen = filedialog.askdirectory(title="Select Folder Containing TV/Anime Videos")
        if chosen:
            self.custom_input_dir = chosen
            self.in_dir_var.set(chosen)
            
            if not self.custom_output_dir:
                default_out = os.path.join(chosen, "compressed")
                os.makedirs(default_out, exist_ok=True)
                self.out_dir_var.set(default_out)

            threading.Thread(target=self._load_files_from_folder_worker, args=(chosen,), daemon=True).start()

    def _select_individual_files(self):
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm"), ("All Files", "*.*")]
        )
        if files:
            if not self.custom_output_dir and self.custom_input_dir:
                pass
            elif not self.custom_output_dir:
                default_out = os.path.join(os.path.dirname(files[0]), "compressed")
                os.makedirs(default_out, exist_ok=True)
                self.out_dir_var.set(default_out)

            for f in files:
                base_name = os.path.basename(f)
                est_size_str = f"~{self.target_size_var.get()} MB" if self.strategy_var.get() == "Target File Size" else "CQ Mode"
                item_id = self.tree.insert("", tk.END, values=(base_name, "Loading...", est_size_str, "Queued"))
                self.task_queue.put({
                    "item_id": item_id,
                    "path": f,
                    "duration": 1440.0,
                    "custom_name": base_name
                })

            self.log(f"Added {len(files)} individual file(s) to queue.")

            def background_probe():
                temp_tasks = list(self.task_queue.queue)
                for task in temp_tasks:
                    f_path = task["path"]
                    item_id = task["item_id"]
                    duration_str, duration_sec = self._get_video_duration(f_path)
                    task["duration"] = duration_sec
                    try:
                        current_vals = self.tree.item(item_id, "values")
                        if current_vals:
                            self.after(0, lambda i=item_id, v0=current_vals[0], d=duration_str, v2=current_vals[2], v3=current_vals[3]: 
                                       self.tree.item(i, values=(v0, d, v2, v3)))
                    except Exception:
                        pass

            threading.Thread(target=background_probe, daemon=True).start()

    def _load_files_from_folder_worker(self, folder_path):
        self.clear_queue()
        valid_exts = (".mp4", ".mkv", ".avi", ".mov", ".webm")
        files = []
        is_recursive = self.recursive_scan_var.get()

        try:
            if is_recursive:
                for root, _, filenames in os.walk(folder_path):
                    for f in filenames:
                        if f.lower().endswith(valid_exts):
                            files.append(os.path.join(root, f))
            else:
                files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(valid_exts)]
            files.sort()
        except Exception as e:
            self.log(f"Error reading folder: {e}")
            return

        if not files:
            self.log(f"No valid video files found in {folder_path}")
            return

        for f in files:
            base_name = os.path.basename(f)
            est_size_str = f"~{self.target_size_var.get()} MB" if self.strategy_var.get() == "Target File Size" else "CQ Mode"
            item_id = self.tree.insert("", tk.END, values=(base_name, "Loading...", est_size_str, "Queued"))
            self.task_queue.put({
                "item_id": item_id,
                "path": f,
                "duration": 1440.0,
                "custom_name": base_name
            })

        scan_type = "recursively" if is_recursive else "flat"
        self.log(f"Loaded {len(files)} file(s) ({scan_type}) from folder: {os.path.basename(folder_path)}")

        def background_probe():
            temp_tasks = list(self.task_queue.queue)
            for task in temp_tasks:
                f_path = task["path"]
                item_id = task["item_id"]
                duration_str, duration_sec = self._get_video_duration(f_path)
                task["duration"] = duration_sec
                try:
                    current_vals = self.tree.item(item_id, "values")
                    if current_vals:
                        self.after(0, lambda i=item_id, v0=current_vals[0], d=duration_str, v2=current_vals[2], v3=current_vals[3]: 
                                   self.tree.item(i, values=(v0, d, v2, v3)))
                except Exception:
                    pass

        threading.Thread(target=background_probe, daemon=True).start()

    def _select_output_dir(self):
        chosen = filedialog.askdirectory(title="Select Output Folder")
        if chosen:
            self.custom_output_dir = chosen
            self.out_dir_var.set(chosen)
            self.log(f"💾 Custom output directory set to: {chosen}")

    def remove_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        selected_ids = set(selected)
        for item_id in selected:
            self.tree.delete(item_id)

        updated_q = queue.Queue()
        while not self.task_queue.empty():
            task = self.task_queue.get()
            if task["item_id"] not in selected_ids:
                updated_q.put(task)
        self.task_queue = updated_q
        self.log(f"Removed {len(selected_ids)} item(s) from queue.")

    def clear_queue(self):
        if self.is_processing:
            messagebox.showwarning("Busy", "Cannot clear queue while encoding is active.")
            return
        self.tree.delete(*self.tree.get_children())
        self.task_queue = queue.Queue()
        self.manual_excluded_streams = {}
        self.log("Queue cleared.")

    def _get_video_duration(self, file_path):
        cmd = [
            self.ffprobe_path, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            duration_sec = float(result.stdout.strip())
            mins = int(duration_sec // 60)
            secs = int(duration_sec % 60)
            return f"{mins:02d}:{secs:02d}", duration_sec
        except Exception:
            return "Unknown", 1440.0

    def inspect_tracks(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select File", "Please select a file in the queue to inspect tracks.")
            return
        
        item_id = selected[0]
        file_path = self._get_path_for_item_id(item_id)

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "File path not found.")
            return

        cmd = [
            self.ffprobe_path, "-v", "error", "-show_entries",
            "stream=index,codec_type,codec_name,channels:stream_tags=language,title",
            "-of", "json", file_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(res.stdout)
            streams = data.get("streams", [])

            t = THEMES[self.current_theme_name]
            dlg = TrackInspectorDialog(self, file_path, streams, t)
            dlg.excluded_tracks = list(self.manual_excluded_streams.get(item_id, []))
            dlg._populate_tracks()
            self.wait_window(dlg)

            self.manual_excluded_streams[item_id] = dlg.excluded_tracks
            if dlg.excluded_tracks:
                self.log(f"Configured track deletions for {os.path.basename(file_path)}: Exclude stream numbers {dlg.excluded_tracks}")

        except Exception as e:
            messagebox.showerror("Probe Failed", f"Could not inspect streams: {e}")

    def open_online_rename(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Queue Empty", "No files in queue to rename.")
            return

        items_data = []
        for task in list(self.task_queue.queue):
            items_data.append({
                "item_id": task["item_id"],
                "path": task["path"],
                "name": task.get("custom_name", os.path.basename(task["path"]))
            })

        t = THEMES[self.current_theme_name]
        dlg = SmartTVDBRenamerDialog(self, items_data, t, parent_app=self)
        self.wait_window(dlg)

        if dlg.result:
            self._handle_rename_dialog_result(dlg.result, dlg.rename_disk_immediately)

    def open_bulk_rename_folder_suite(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Queue Empty", "No files in queue to rename.")
            return

        items_data = []
        for task in list(self.task_queue.queue):
            items_data.append({
                "item_id": task["item_id"],
                "path": task["path"],
                "name": task.get("custom_name", os.path.basename(task["path"]))
            })

        t = THEMES[self.current_theme_name]
        dlg = BulkRenameAndFolderDialog(self, items_data, t)
        self.wait_window(dlg)

        if dlg.result:
            self._handle_rename_dialog_result(dlg.result, dlg.rename_disk_immediately)

    def _handle_rename_dialog_result(self, result_map, rename_disk_immediately):
        if rename_disk_immediately:
            renamed_count = [0]
            skipped_count = [0]
            session_moves = []
            
            if self.custom_output_dir:
                base_target_dir = self.custom_output_dir
            elif not self.task_queue.empty():
                base_target_dir = os.path.dirname(list(self.task_queue.queue)[0]["path"])
            else:
                base_target_dir = ""

            def disk_worker():
                updated_queue = queue.Queue()
                while not self.task_queue.empty():
                    task = self.task_queue.get()
                    item_id = task["item_id"]
                    old_path = task["path"]
                    
                    target_res = next((res for res in result_map if res["item_id"] == item_id), None)
                    if target_res:
                        if target_res.get("is_skipped", False):
                            skipped_count[0] += 1
                            self.log(f"⏭️ Skipped Special Episode (Left Untouched): {os.path.basename(old_path)}")
                            updated_queue.put(task)
                            continue

                        new_name = target_res["new_name"]
                        season_folder = target_res.get("season_folder", "")
                        
                        if season_folder:
                            season_dir = os.path.join(base_target_dir, season_folder)
                            os.makedirs(season_dir, exist_ok=True)
                            new_path = os.path.join(season_dir, new_name)
                        else:
                            new_path = os.path.join(base_target_dir, new_name)

                        try:
                            if old_path != new_path and os.path.exists(old_path):
                                shutil.move(old_path, new_path)
                                session_moves.append({"current_path": new_path, "original_path": old_path, "season_dir": season_dir if season_folder else ""})
                                task["path"] = new_path
                                task["custom_name"] = new_name
                                renamed_count[0] += 1
                                
                                self.after(0, lambda i=item_id, n=new_name, sf=season_folder: self.tree.item(
                                    i, values=(n, self.tree.item(i)["values"][1], self.tree.item(i)["values"][2], f"Moved to {sf} ✅" if sf else "Renamed ✅")
                                ))
                        except Exception as err:
                            self.log(f"❌ Failed to organize {os.path.basename(old_path)}: {err}")
                    updated_queue.put(task)
                
                self.task_queue = updated_queue
                
                if session_moves:
                    self.rename_undo_history.append(session_moves)

                self.log(f"⚡ Successfully organized {renamed_count[0]} file(s).")
                self.after(0, lambda: messagebox.showinfo("Organization Complete", f"Successfully processed {renamed_count[0]} file(s)."))

            threading.Thread(target=disk_worker, daemon=True).start()
        else:
            rename_map = {res["item_id"]: res for res in result_map}
            updated_queue = queue.Queue()
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task["item_id"] in rename_map:
                    res_item = rename_map[task["item_id"]]
                    if not res_item.get("is_skipped", False):
                        new_name = res_item["new_name"]
                        task["custom_name"] = new_name
                        self.tree.item(task["item_id"], values=(new_name, self.tree.item(task["item_id"])["values"][1], self.tree.item(task["item_id"])["values"][2], "Queued"))
                updated_queue.put(task)
            
            self.task_queue = updated_queue
            self.log(f"Applied renames to queue.")

    def undo_last_rename(self):
        if not self.rename_undo_history:
            messagebox.showinfo("Nothing to Undo", "No recent rename history available.", parent=self)
            return

        ans = messagebox.askyesno(
            "Confirm Undo",
            "Are you sure you want to revert the last rename action? Files will be moved back to their original paths.",
            parent=self
        )
        if not ans:
            return

        last_moves = self.rename_undo_history.pop()
        reverted_count = 0

        def undo_worker():
            nonlocal reverted_count
            updated_queue = queue.Queue()
            path_map = {m["current_path"]: m for m in last_moves}

            while not self.task_queue.empty():
                task = self.task_queue.get()
                curr_path = task["path"]
                
                if curr_path in path_map:
                    orig_path = path_map[curr_path]["original_path"]
                    season_dir = path_map[curr_path]["season_dir"]
                    try:
                        if os.path.exists(curr_path):
                            os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                            shutil.move(curr_path, orig_path)
                            task["path"] = orig_path
                            task["custom_name"] = os.path.basename(orig_path)
                            reverted_count += 1
                            
                            if season_dir:
                                try:
                                    if os.path.exists(season_dir) and not os.listdir(season_dir):
                                        os.rmdir(season_dir)
                                except Exception:
                                    pass

                            self.after(0, lambda i=task["item_id"], orig_name=os.path.basename(orig_path): self.tree.item(
                                i, values=(orig_name, self.tree.item(i)["values"][1], self.tree.item(i)["values"][2], "Reverted 🔄")
                            ))
                    except Exception as e:
                        self.log(f"❌ Failed to revert {os.path.basename(curr_path)}: {e}")
                updated_queue.put(task)

            self.task_queue = updated_queue
            self.log(f"🔄 Successfully reverted {reverted_count} file(s) back to original locations.")
            self.after(0, lambda: messagebox.showinfo("Undo Complete", f"Successfully reverted {reverted_count} file(s) to their original names and paths.", parent=self))

        threading.Thread(target=undo_worker, daemon=True).start()

    def _get_path_for_item_id(self, item_id):
        temp_queue = list(self.task_queue.queue)
        for task in temp_queue:
            if task["item_id"] == item_id:
                return task["path"]
        return None

    def start_preview(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Video", "Please select a video file in the queue to run a 3-minute clip preview.")
            return

        if self.is_processing:
            messagebox.showwarning("Busy", "Encoder is busy processing tasks.")
            return

        item_id = selected[0]
        file_path = self._get_path_for_item_id(item_id)
        if not file_path:
            messagebox.showerror("Error", "Could not locate task in queue.")
            return

        duration_str, duration_sec = self._get_video_duration(file_path)

        start_time = simpledialog.askstring(
            "Scene Preview Clip",
            f"Enter start time for 3-minute clip (HH:MM:SS or seconds):\n(Video duration: {duration_str})",
            initialvalue="00:03:00",
            parent=self
        )

        if not start_time:
            return

        target_task = None
        temp_list = list(self.task_queue.queue)
        for task in temp_list:
            if task["item_id"] == item_id:
                target_task = task
                break

        if target_task:
            self.is_processing = True
            self.stop_requested = False
            self.start_btn.config(state="disabled")
            self.single_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            threading.Thread(target=self._run_preview_worker, args=(target_task, start_time.strip()), daemon=True).start()

    def _run_preview_worker(self, task, start_time):
        input_path = task["path"]
        duration_sec = task["duration"]
        item_id = task["item_id"]

        out_dir = os.path.join(self.user_data_dir, "preview")
        os.makedirs(out_dir, exist_ok=True)

        count = 1
        while os.path.exists(os.path.join(out_dir, f"preview {count}.mkv")):
            count += 1
        output_path = os.path.join(out_dir, f"preview {count}.mkv")

        base_name = task.get("custom_name", os.path.basename(input_path))
        self.log(f"--- STARTING 3-MINUTE PREVIEW CLIP ({os.path.basename(output_path)}, Start: {start_time}) ---")
        self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], "Testing...", f"Encoding {os.path.basename(output_path)}..."))

        cmd = self._build_ffmpeg_command(input_path, output_path, duration_sec, item_id=item_id, is_preview=True, preview_start=start_time)
        success = self._run_ffmpeg_process(cmd, item_id, 180.0)

        if success and os.path.exists(output_path):
            clip_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            est_full_mb = (clip_size_mb / 180.0) * duration_sec
            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], f"~{est_full_mb:.1f} MB", f"Done: preview {count}.mkv ({clip_size_mb:.1f} MB)"))
            self.log(f"Finished Preview Clip: {clip_size_mb:.2f} MB saved as {output_path}")
        else:
            status = "Stopped 🛑" if self.stop_requested else "Preview Failed ❌"
            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], "Error", status))

        self.is_processing = False
        self.start_btn.config(state="normal")
        self.single_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def stop_encoding(self):
        if not self.is_processing:
            return
        
        self.stop_requested = True
        self.log("🛑 Stop requested! Terminating active process...")
        if self.current_proc:
            try:
                self.current_proc.kill()
            except Exception as e:
                self.log(f"Error stopping process: {e}")

    def start_single(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select File", "Please select a file in the table queue to encode.")
            return

        if self.is_processing:
            return

        item_id = selected[0]
        target_task = None
        temp_list = list(self.task_queue.queue)
        for task in temp_list:
            if task["item_id"] == item_id:
                target_task = task
                break

        if target_task:
            self.is_processing = True
            self.stop_requested = False
            self.start_btn.config(state="disabled")
            self.single_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            threading.Thread(target=self._run_single_worker, args=(target_task,), daemon=True).start()

    def _check_collision_and_handle(self, output_path):
        if not os.path.exists(output_path):
            return True

        mode = self.collision_var.get()
        if "Skip" in mode:
            self.log(f"⏭️ Output file already exists. Skipping: {os.path.basename(output_path)}")
            return False
        elif "Overwrite" in mode:
            self.log(f"⚠️ Output file exists. Overwriting: {os.path.basename(output_path)}")
            try:
                os.remove(output_path)
            except Exception:
                pass
            return True
        else:
            ans = messagebox.askyesno(
                "File Exists",
                f"Output file already exists:\n{os.path.basename(output_path)}\n\nDo you want to overwrite it?",
                parent=self
            )
            if ans:
                try:
                    os.remove(output_path)
                except Exception:
                    pass
                return True
            else:
                return False

    def _run_single_worker(self, task):
        item_id = task["item_id"]
        input_path = task["path"]
        duration = task["duration"]

        out_dir = self.custom_output_dir if self.custom_output_dir else os.path.join(os.path.dirname(input_path), "compressed")
        os.makedirs(out_dir, exist_ok=True)
        
        base_name = task.get("custom_name", os.path.basename(input_path))
        raw_name, _ = os.path.splitext(base_name)
        suffix_tags = self._get_filename_tags()
        
        output_filename = f"{raw_name}{suffix_tags}.mkv"
        output_path = os.path.join(out_dir, output_filename)

        if not self._check_collision_and_handle(output_path):
            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], self.tree.item(item_id)["values"][2], "Skipped (Exists) ⏭️"))
            self.is_processing = False
            self.start_btn.config(state="normal")
            self.single_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            return

        self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], self.tree.item(item_id)["values"][2], "Encoding..."))
        cmd = self._build_ffmpeg_command(input_path, output_path, duration, item_id=item_id)
        
        self.log(f"Starting single encode: {output_filename}")
        success = self._run_ffmpeg_process(cmd, item_id, duration)

        if not success and ("nvenc" in self.encoder_var.get() or "qsv" in self.encoder_var.get()) and not self.stop_requested:
            self.log(f"⚠️ Hardware encoder failed. Automatically falling back to CPU software encoder (libsvtav1)...")
            cmd = self._build_ffmpeg_command(input_path, output_path, duration, item_id=item_id, force_fallback_cpu=True)
            success = self._run_ffmpeg_process(cmd, item_id, duration)

        if success and os.path.exists(output_path):
            out_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], f"{out_size_mb:.1f} MB", f"Done ✅ ({out_size_mb:.1f} MB)"))
            self.log(f"Finished: {output_filename} -> Size: {out_size_mb:.1f} MB")
        else:
            status = "Stopped 🛑" if self.stop_requested else "Failed ❌"
            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], "Error", status))

        self.is_processing = False
        self.start_btn.config(state="normal")
        self.single_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def start_batch(self):
        if self.task_queue.empty():
            messagebox.showinfo("Queue Empty", "Please load a folder or add video files before starting.")
            return

        if self.is_processing:
            return

        self.is_processing = True
        self.stop_requested = False
        self.start_btn.config(state="disabled")
        self.single_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        threading.Thread(target=self._process_queue_worker, daemon=True).start()

    def _process_queue_worker(self):
        temp_queue = list(self.task_queue.queue)

        for task in temp_queue:
            if self.stop_requested:
                self.log("🛑 Batch transcode stopped by user.")
                break

            item_id = task["item_id"]
            input_path = task["path"]
            duration = task["duration"]

            out_dir = self.custom_output_dir if self.custom_output_dir else os.path.join(os.path.dirname(input_path), "compressed")
            os.makedirs(out_dir, exist_ok=True)
            
            base_name = task.get("custom_name", os.path.basename(input_path))
            raw_name, _ = os.path.splitext(base_name)
            suffix_tags = self._get_filename_tags()

            output_filename = f"{raw_name}{suffix_tags}.mkv"
            output_path = os.path.join(out_dir, output_filename)

            if not self._check_collision_and_handle(output_path):
                self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], self.tree.item(item_id)["values"][2], "Skipped (Exists) ⏭️"))
                continue

            self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], self.tree.item(item_id)["values"][2], "Encoding..."))
            
            cmd = self._build_ffmpeg_command(input_path, output_path, duration, item_id=item_id)
            self.log(f"Starting: {output_filename}")

            success = self._run_ffmpeg_process(cmd, item_id, duration)

            if not success and ("nvenc" in self.encoder_var.get() or "qsv" in self.encoder_var.get()) and not self.stop_requested:
                self.log(f"⚠️ Hardware encoder failed. Automatically falling back to CPU software encoder (libsvtav1)...")
                cmd = self._build_ffmpeg_command(input_path, output_path, duration, item_id=item_id, force_fallback_cpu=True)
                success = self._run_ffmpeg_process(cmd, item_id, duration)

            if success and os.path.exists(output_path):
                out_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], f"{out_size_mb:.1f} MB", f"Done ✅ ({out_size_mb:.1f} MB)"))
                self.log(f"Finished: {output_filename} -> Size: {out_size_mb:.1f} MB")
            else:
                status = "Stopped 🛑" if self.stop_requested else "Failed ❌"
                self.tree.item(item_id, values=(base_name, self.tree.item(item_id)["values"][1], "Error", status))

        self.is_processing = False
        self.start_btn.config(state="normal")
        self.single_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log("Batch processing sequence finished!")

        if self.sound_notify_var.get() and winsound and not self.stop_requested:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        if self.auto_shutdown_var.get() and not self.stop_requested:
            self.log("🌙 Auto-shutdown triggered. Shutting down system in 30 seconds...")
            if sys.platform == "win32":
                os.system("shutdown /s /t 30")

    def _build_ffmpeg_command(self, input_path, output_path, duration_sec, item_id=None, is_preview=False, preview_start="00:03:00", force_fallback_cpu=False):
        encoder_selection = self.encoder_var.get()
        audio_selection = self.audio_var.get()
        sub_selection = self.sub_var.get()
        aspect_selection = self.aspect_var.get()
        strategy = self.strategy_var.get()
        audio_remove_selection = self.audio_track_remove_var.get()

        sub_tracks_to_remove = [t.strip() for t in self.sub_track_remove_var.get().split(",") if t.strip().isdigit()]

        cmd = [self.ffmpeg_path, "-y"]

        if is_preview:
            cmd.extend(["-ss", preview_start])

        if "nvenc" in encoder_selection and not is_preview and not force_fallback_cpu:
            cmd.extend(["-hwaccel", "cuda"])

        cmd.extend(["-i", input_path])

        if is_preview:
            cmd.extend(["-t", "00:03:00"])

        cmd.extend(["-map", "0:v:0"])

        if "Remove All Audio" in audio_selection:
            cmd.append("-an")
            audio_bitrate_kbps = 0
        else:
            cmd.extend(["-map", "0:a?"])
            if audio_selection.startswith("Opus"):
                cmd.extend(["-c:a", "libopus", "-b:a", "48k", "-ac", "2"])
                audio_bitrate_kbps = 48
            elif audio_selection.startswith("AAC"):
                cmd.extend(["-c:a", "aac", "-b:a", "96k", "-ac", "2"])
                audio_bitrate_kbps = 96
            else:
                cmd.extend(["-c:a", "copy"])
                audio_bitrate_kbps = 128

        if "Track 1" in audio_remove_selection:
            cmd.extend(["-map", "-0:a:0"])
        elif "Track 2" in audio_remove_selection:
            cmd.extend(["-map", "-0:a:1"])
        elif "Track 3" in audio_remove_selection:
            cmd.extend(["-map", "-0:a:2"])
        elif "Track 4" in audio_remove_selection:
            cmd.extend(["-map", "-0:a:3"])
        elif "Track 5" in audio_remove_selection:
            cmd.extend(["-map", "-0:a:4"])

        if "Strip All" in sub_selection:
            cmd.append("-sn")
        else:
            cmd.extend(["-map", "0:s?", "-c:s", "copy"])

        for s_idx in sub_tracks_to_remove:
            cmd.extend(["-map", f"-0:s:{s_idx}"])

        if item_id and item_id in self.manual_excluded_streams:
            for ex_idx in self.manual_excluded_streams[item_id]:
                cmd.extend(["-map", f"-0:{ex_idx}"])

        filter_chain = []
        if "1920x1080" in aspect_selection:
            filter_chain.append("scale=1920:1080")
        elif "1280x720" in aspect_selection:
            filter_chain.append("scale=1280:720")
        elif "854x480" in aspect_selection:
            filter_chain.append("scale=854:480")
        elif "640x360" in aspect_selection:
            filter_chain.append("scale=640:360")
        elif "1440x1080" in aspect_selection:
            filter_chain.append("scale=1440:1080")
        elif "2560x1080" in aspect_selection:
            filter_chain.append("scale=2560:1080")

        if filter_chain:
            cmd.extend(["-vf", ",".join(filter_chain)])

        if force_fallback_cpu:
            cmd.extend(["-c:v", "libsvtav1", "-preset", "5", "-pix_fmt", "yuv420p10le"])
        elif "av1_nvenc" in encoder_selection:
            cmd.extend(["-c:v", "av1_nvenc", "-pix_fmt", "p010le", "-preset", "p7"])
        elif "hevc_nvenc" in encoder_selection:
            cmd.extend(["-c:v", "hevc_nvenc", "-pix_fmt", "p010le", "-preset", "p7"])
        elif "av1_qsv" in encoder_selection:
            cmd.extend(["-c:v", "av1_qsv", "-pix_fmt", "p010le", "-preset", "veryslow"])
        else:
            cmd.extend(["-c:v", "libsvtav1", "-preset", "5", "-pix_fmt", "yuv420p10le"])

        if strategy == "Target File Size":
            target_mb = float(self.target_size_var.get())
            calc_duration = 180.0 if is_preview else duration_sec
            total_bitrate_kbps = (target_mb * 8192) / calc_duration
            video_bitrate_kbps = max(int(total_bitrate_kbps - audio_bitrate_kbps), 100)
            
            cmd.extend([
                "-b:v", f"{video_bitrate_kbps}k",
                "-maxrate", f"{int(video_bitrate_kbps * 1.5)}k",
                "-bufsize", f"{int(video_bitrate_kbps * 3)}k"
            ])
        else:
            cq_val = self.target_size_var.get()
            if "nvenc" in encoder_selection and not force_fallback_cpu:
                cmd.extend(["-cq", cq_val, "-rc", "vbr"])
            else:
                cmd.extend(["-crf", cq_val])

        cmd.append(output_path)
        return cmd

    def _run_ffmpeg_process(self, cmd, item_id, total_duration):
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.current_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            for line in self.current_proc.stdout:
                line_str = line.strip()
                if line_str:
                    try:
                        with open(self.session_log_path, "a", encoding="utf-8") as f:
                            f.write(f"[FFmpeg] {line_str}\n")
                    except Exception:
                        pass

                if "time=" in line:
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        parts = time_str.split(":")
                        elapsed = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                        pct = min(int((elapsed / total_duration) * 100), 100)
                        self.tree.item(item_id, values=(self.tree.item(item_id)["values"][0], self.tree.item(item_id)["values"][1], self.tree.item(item_id)["values"][2], f"Encoding... {pct}%"))
                    except Exception:
                        pass

            self.current_proc.wait()
            rc = self.current_proc.returncode
            self.current_proc = None
            return rc == 0
        except Exception as e:
            self.log(f"Error executing process: {e}")
            self.current_proc = None
            return False

if __name__ == "__main__":
    app = GreedyMediaApp()
    app.mainloop()