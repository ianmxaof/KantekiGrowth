import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import threading
import os
import sys
import traceback
import subprocess
import time
import psutil

# Import main logic from the launcher
import ian_mode_launcher

LOG_PATH = ian_mode_launcher.LOG_PATH

DARK_BG = '#23272e'
DARK_FG = '#e0e0e0'
ACCENT = '#3a3f4b'
BUTTON_BG = '#393e46'
BUTTON_FG = '#f8f8f2'
HIGHLIGHT = '#5c6370'
ERROR_COLOR = '#ff5555'
SUCCESS_COLOR = '#50fa7b'

class LauncherGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IAN MODE LAUNCHER GUI")
        self.geometry("650x520")
        self.configure(bg=DARK_BG)
        self.status_var = tk.StringVar(value="Ready")
        self.log_health = tk.StringVar(value="")
        self.selected_file = tk.StringVar(value="")
        self.create_widgets()
        self.automated_startup()

    def create_widgets(self):
        # File browser row
        file_frame = tk.Frame(self, bg=DARK_BG)
        file_frame.pack(pady=(10, 0))
        tk.Label(file_frame, text="Choose Python file to build:", bg=DARK_BG, fg=DARK_FG, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 8))
        file_entry = tk.Entry(file_frame, textvariable=self.selected_file, width=48, font=("Consolas", 10), bg=ACCENT, fg=DARK_FG, insertbackground=DARK_FG, borderwidth=0, highlightthickness=1, highlightbackground=HIGHLIGHT)
        file_entry.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(file_frame, text="Browse", command=self.browse_file, bg=BUTTON_BG, fg=BUTTON_FG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 10), width=10).pack(side=tk.LEFT)
        # Build .exe button
        build_btn = tk.Button(file_frame, text="Build .exe", command=self.build_exe, bg=SUCCESS_COLOR, fg=DARK_BG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 10, "bold"), width=12)
        build_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.build_btn = build_btn
        self.selected_file.trace_add('write', self._toggle_build_btn)
        header = tk.Label(self, text="IAN MODE LAUNCHER", font=("Segoe UI", 20, "bold"), bg=DARK_BG, fg=SUCCESS_COLOR)
        header.pack(pady=(18, 2))
        status = tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 12), fg=SUCCESS_COLOR, bg=DARK_BG)
        status.pack(pady=(0, 8))
        btn_frame = tk.Frame(self, bg=DARK_BG)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Run Launcher", command=self.run_launcher, bg=BUTTON_BG, fg=BUTTON_FG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 11, "bold"), width=14).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Clean Logs", command=self.clean_logs, bg=BUTTON_BG, fg=BUTTON_FG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 11), width=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Show Log Directory", command=self.show_log_dir, bg=BUTTON_BG, fg=BUTTON_FG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 11), width=18).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Exit", command=self.destroy, bg=ERROR_COLOR, fg=BUTTON_FG, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 11), width=8).pack(side=tk.LEFT, padx=6)
        # Add One-Click Update button below main buttons
        update_btn = tk.Button(self, text="One-Click Update", command=self.one_click_update, bg=BUTTON_BG, fg=SUCCESS_COLOR, activebackground=HIGHLIGHT, activeforeground=DARK_FG, font=("Segoe UI", 10, "bold"), width=18)
        update_btn.pack(pady=(0, 10))
        self.update_btn = update_btn
        tk.Label(self, text="Log Health:", bg=DARK_BG, fg=DARK_FG, font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        log_health_label = tk.Label(self, textvariable=self.log_health, font=("Segoe UI", 10), fg=SUCCESS_COLOR, bg=DARK_BG)
        log_health_label.pack()
        tk.Label(self, text="Errors/Warnings:", bg=DARK_BG, fg=DARK_FG, font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        self.error_box = scrolledtext.ScrolledText(self, height=8, width=78, state='disabled', bg=ACCENT, fg=DARK_FG, insertbackground=DARK_FG, font=("Consolas", 10), borderwidth=0, highlightthickness=1, highlightbackground=HIGHLIGHT)
        self.error_box.pack(pady=(2, 10))

    def run_launcher(self):
        self.status_var.set("Running...")
        self.error_box.config(state='normal')
        self.error_box.delete(1.0, tk.END)
        self.error_box.config(state='disabled')
        t = threading.Thread(target=self._run_launcher_thread)
        t.start()

    def _run_launcher_thread(self):
        try:
            logfile = os.path.join(LOG_PATH, 'ian_mode_launcher.log')
            kill_process_locking_file(logfile)
            ian_mode_launcher.main()
            self.status_var.set("Success!")
        except Exception as e:
            self.status_var.set("Error!")
            self.append_error(traceback.format_exc())
        self.refresh_log_health()

    def clean_logs(self):
        try:
            ian_mode_launcher.clean_invalid_logs()
            self.append_error("[INFO] Cleaned invalid logs.")
        except Exception as e:
            self.append_error(f"[ERROR] {e}")
        self.refresh_log_health()

    def show_log_dir(self):
        log_dir = os.path.abspath(LOG_PATH)
        if os.path.exists(log_dir):
            if sys.platform == "win32":
                os.startfile(log_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", log_dir])
            else:
                subprocess.Popen(["xdg-open", log_dir])
        else:
            self.append_error(f"[ERROR] Log directory does not exist: {log_dir}")

    def refresh_log_health(self):
        try:
            if not os.path.exists(LOG_PATH):
                self.log_health.set("Log directory does not exist.")
                return
            files = os.listdir(LOG_PATH)
            if not files:
                self.log_health.set("Log directory is empty.")
                return
            good, bad = 0, 0
            for fname in files:
                try:
                    with open(os.path.join(LOG_PATH, fname), 'r') as f:
                        import json
                        json.load(f)
                    good += 1
                except Exception:
                    bad += 1
            self.log_health.set(f"{good} valid logs, {bad} invalid logs.")
        except Exception as e:
            self.log_health.set(f"[ERROR] {e}")

    def append_error(self, msg):
        self.error_box.config(state='normal')
        self.error_box.insert(tk.END, msg + "\n")
        self.error_box.config(state='disabled')
        self.error_box.see(tk.END)

    def automated_startup(self):
        # Automated startup: ensure all required files/dirs, log resolved paths
        ian_mode_launcher.log_resolved_paths()
        ian_mode_launcher.ensure_dir(ian_mode_launcher.LOG_PATH)
        ian_mode_launcher.ensure_file(ian_mode_launcher.INSTRUCTIONS_PATH, {"instructions": ["Default Ian Mode instruction set"], "priority_tags": []})
        ian_mode_launcher.ensure_file(ian_mode_launcher.NEXT_GEN_PATH, {"instructions": [], "priority_tags": []})
        ian_mode_launcher.ensure_file(ian_mode_launcher.CHANGELOG_PATH, {"generated": "", "summary": {}, "note": ""})
        self.refresh_log_health()

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Python file",
            filetypes=[("Python Files", "*.py")],
            initialdir=os.getcwd()
        )
        if file_path:
            self.selected_file.set(file_path)

    def _toggle_build_btn(self, *args):
        if self.selected_file.get() and os.path.isfile(self.selected_file.get()):
            self.build_btn.config(state='normal')
        else:
            self.build_btn.config(state='disabled')

    def build_exe(self):
        py_file = self.selected_file.get()
        if not py_file or not os.path.isfile(py_file):
            self.append_error('[ERROR] No valid Python file selected.')
            return
        self.status_var.set('Building .exe...')
        self.error_box.config(state='normal')
        self.error_box.delete(1.0, tk.END)
        self.error_box.config(state='disabled')
        t = threading.Thread(target=self._build_exe_thread, args=(py_file,))
        t.start()

    def _build_exe_thread(self, py_file):
        try:
            icon_path = r'E:/projects/icon_placeholders/favicon.ico'
            cmd = [sys.executable, '-m', 'PyInstaller', '--onefile', '--icon', icon_path, py_file]
            self.append_error(f'[BUILD] Running: {" ".join(cmd)}')
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc.stdout:
                self.append_error(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self.status_var.set('Build Success! .exe in dist/')
                self.append_error('[SUCCESS] Build complete.')
            else:
                self.status_var.set('Build Failed!')
                self.append_error('[ERROR] Build failed.')
        except Exception as e:
            self.status_var.set('Build Error!')
            self.append_error(f'[ERROR] {e}')

    def one_click_update(self):
        # Stub: In real use, check GitHub for new release, download latest .exe, replace current, notify user
        messagebox.showinfo("Update", "[STUB] Would check GitHub for new release and download latest .exe.")

def kill_process_locking_file(filepath, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            with open(filepath, 'a'):
                return True  # File is accessible
        except PermissionError as e:
            # Find and kill the process locking the file
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    flist = proc.info.get('open_files') or []
                    for f in flist:
                        if os.path.abspath(f.path) == os.path.abspath(filepath):
                            print(f"[ERROR-PROOF] Killing process {proc.pid} ({proc.name()}) locking {filepath}")
                            proc.kill()
                            time.sleep(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(1)
    # Final attempt
    try:
        with open(filepath, 'a'):
            return True
    except Exception as e:
        print(f"[FATAL] Could not access {filepath} after killing processes: {e}")
        return False

if __name__ == "__main__":
    app = LauncherGUI()
    app.mainloop()
