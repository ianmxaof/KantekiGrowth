import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import psutil
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading
import json
import shutil

# --- Logging Setup ---
LOG_FILE = 'bootstrap_gui.log'
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def log_action(msg):
    try:
        logging.info(msg)
    except Exception as e:
        print(f'Log write error: {e}')

# --- Settings ---
SETTINGS_FILE = 'bootstrap_gui_settings.json'
DEFAULT_EXE = os.path.join('dist', 'MAIN_LAUNCHER.EXE')
DEFAULT_GUI = 'ian_mode_launcher_gui.py'

class Settings:
    def __init__(self):
        self.telegram_mode = False
        self.cli_mode = False
        self.program_path = DEFAULT_EXE
        self.gui_path = DEFAULT_GUI
    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                self.telegram_mode = data.get('telegram_mode', False)
                self.cli_mode = data.get('cli_mode', False)
                self.program_path = data.get('program_path', DEFAULT_EXE)
                self.gui_path = data.get('gui_path', DEFAULT_GUI)
            except Exception:
                pass
    def save(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({
                    'telegram_mode': self.telegram_mode,
                    'cli_mode': self.cli_mode,
                    'program_path': self.program_path,
                    'gui_path': self.gui_path
                }, f, indent=2)
        except Exception:
            pass

# --- Modern Dark Theme ---
def set_dark_theme(root):
    style = ttk.Style(root)
    root.tk_setPalette(background='#23272a', foreground='#ffffff', activeBackground='#2c2f33', activeForeground='#ffffff')
    style.theme_use('clam')
    style.configure('.', background='#23272a', foreground='#ffffff', fieldbackground='#2c2f33', font=('Segoe UI', 11))
    style.configure('TButton', background='#2c2f33', foreground='#ffffff', borderwidth=1, focusthickness=2, focuscolor='#7289da')
    style.map('TButton', background=[('active', '#7289da')], foreground=[('active', '#ffffff')])
    style.configure('TCheckbutton', background='#23272a', foreground='#ffffff')
    style.configure('TLabel', background='#23272a', foreground='#ffffff')
    style.configure('TEntry', fieldbackground='#2c2f33', foreground='#ffffff')
    style.configure('TFrame', background='#23272a')

class BootstrapGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Ian Mode Launcher Bootstrapper')
        self.geometry('600x500')
        set_dark_theme(self)
        self.settings = Settings()
        self.settings.load()
        self.create_widgets()
        self.update_status()
        self.update_log_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        ttk.Label(main_frame, text='IAN MODE LAUNCHER', font=('Segoe UI', 18, 'bold')).pack(pady=(0, 10))
        # Toggles
        toggles_frame = ttk.Frame(main_frame)
        toggles_frame.pack(pady=5, fill='x')
        self.telegram_var = tk.BooleanVar(value=self.settings.telegram_mode)
        self.cli_var = tk.BooleanVar(value=self.settings.cli_mode)
        ttk.Checkbutton(toggles_frame, text='Telegram Bot Mode', variable=self.telegram_var, command=self.save_settings).pack(side='left', padx=10)
        ttk.Checkbutton(toggles_frame, text='CLI Mode', variable=self.cli_var, command=self.save_settings).pack(side='left', padx=10)
        # Browse Program
        browse_frame = ttk.Frame(main_frame)
        browse_frame.pack(pady=10, fill='x')
        ttk.Label(browse_frame, text='Program:').pack(side='left')
        self.program_path_var = tk.StringVar(value=self.settings.program_path)
        ttk.Entry(browse_frame, textvariable=self.program_path_var, width=40, state='readonly').pack(side='left', padx=5)
        ttk.Button(browse_frame, text='Browse', command=self.browse_program).pack(side='left')
        # Launch/Control Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text='Launch MAIN_LAUNCHER.EXE', command=self.launch_main_exe).pack(side='left', padx=10)
        ttk.Button(btn_frame, text='Launch GUI Configurator', command=self.launch_gui).pack(side='left', padx=10)
        ttk.Button(btn_frame, text='Quit', command=self.quit_all).pack(side='left', padx=10)
        # Status
        self.status_label = ttk.Label(main_frame, text='', font=('Segoe UI', 10, 'italic'))
        self.status_label.pack(pady=5)
        # Log Output
        ttk.Label(main_frame, text='Log Output:').pack(pady=(10, 0))
        self.log_window = scrolledtext.ScrolledText(main_frame, height=8, width=70, state='disabled', bg='#2c2f33', fg='#ffffff', insertbackground='#ffffff')
        self.log_window.pack(pady=5)

    def save_settings(self):
        self.settings.telegram_mode = self.telegram_var.get()
        self.settings.cli_mode = self.cli_var.get()
        self.settings.program_path = self.program_path_var.get()
        self.settings.save()

    def browse_program(self):
        path = filedialog.askopenfilename(title='Select Program', filetypes=[('Executables', '*.exe'), ('All Files', '*.*')])
        if path:
            self.program_path_var.set(path)
            self.save_settings()

    def update_status(self):
        exe_status = self.get_process_status(os.path.basename(self.program_path_var.get()))
        gui_status = self.get_process_status(os.path.basename(self.settings.gui_path))
        status = f"MAIN_LAUNCHER.EXE: {exe_status} | GUI: {gui_status}"
        self.status_label.config(text=status)
        self.after(2000, self.update_status)

    def update_log_window(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()[-15:]
                self.log_window.config(state='normal')
                self.log_window.delete(1.0, tk.END)
                self.log_window.insert(tk.END, ''.join(lines))
                self.log_window.config(state='disabled')
        except Exception as e:
            self.log_window.config(state='normal')
            self.log_window.delete(1.0, tk.END)
            self.log_window.insert(tk.END, f'Log read error: {e}\n')
            self.log_window.config(state='disabled')
        self.after(2000, self.update_log_window)

    def get_process_status(self, name):
        for proc in psutil.process_iter(['name', 'cmdline', 'status']):
            try:
                if name.lower() in proc.info['name'].lower() or (proc.info['cmdline'] and name.lower() in ' '.join(proc.info['cmdline']).lower()):
                    status = proc.info.get('status', '')
                    if status == psutil.STATUS_ZOMBIE:
                        return 'ZOMBIE'
                    elif status == psutil.STATUS_STOPPED:
                        return 'STOPPED'
                    elif status == psutil.STATUS_RUNNING:
                        return 'RUNNING'
                    else:
                        return status.upper()
            except Exception:
                continue
        return 'STOPPED'

    def launch_main_exe(self):
        exe_path = self.program_path_var.get()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror('Missing File', f'{exe_path} not found.')
            return
        try:
            subprocess.Popen([exe_path] + self.get_launch_args())
            log_action('Launched MAIN_LAUNCHER.EXE.')
        except Exception as e:
            log_action(f'Error launching MAIN_LAUNCHER.EXE: {e}')
            messagebox.showerror('Error', f'Error launching MAIN_LAUNCHER.EXE: {e}')

    def launch_gui(self):
        gui_path = self.settings.gui_path
        if not gui_path or not os.path.exists(gui_path):
            messagebox.showerror('Missing File', f'{gui_path} not found.')
            return
        try:
            subprocess.Popen([sys.executable, gui_path])
            log_action('Launched GUI Configurator.')
        except Exception as e:
            log_action(f'Error launching GUI Configurator: {e}')
            messagebox.showerror('Error', f'Error launching GUI Configurator: {e}')

    def get_launch_args(self):
        args = []
        if self.telegram_var.get():
            args.append('--telegram')
        if self.cli_var.get():
            args.append('--interactive')
        return args

    def quit_all(self):
        log_action('Bootstrap GUI exited.')
        self.destroy()

if __name__ == '__main__':
    app = BootstrapGUI()
    app.mainloop() 