"""
Main GUI window for OrganizerBot
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from organizerbot.core.config import load_config, save_config
from organizerbot.core.watcher import FileEventHandler, start_file_watcher
from organizerbot.utils.logger import log_action, gui_queue
import threading
import queue
import time
from collections import defaultdict
from pathlib import Path
from organizerbot.gui.review_window import ReviewWindow
import pystray
from PIL import Image, ImageDraw

class MainWindow:
    def __init__(self):
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.root = ctk.CTk()
        self.root.title("OrganizerBot")
        self.root.geometry("1000x800")
        self.config = load_config()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'category_counts': defaultdict(int),
            'last_processed': None,
            'progress': 0
        }
        
        # Tray icon
        self.tray_icon = None
        self.tray_enabled = False
        
        # Create and start the file watcher
        self.watcher_thread = None
        self.observer = None
        self.review_window = None
        self.setup_ui()
        self.load_config()
        
        # Start automatic updates
        self.root.after(100, self.update_log)
        self.root.after(1000, self.update_stats)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top section - Controls
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Watch Folder
        watch_frame = ctk.CTkFrame(control_frame)
        watch_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(watch_frame, text="Watch Folder:").pack(side="left", padx=5)
        self.watch_folder_var = ctk.StringVar(value=self.config.watch_folder)
        ctk.CTkEntry(watch_frame, textvariable=self.watch_folder_var, width=300).pack(side="left", padx=5)
        ctk.CTkButton(watch_frame, text="Browse", command=self.choose_watch_folder).pack(side="left", padx=5)
        
        # Source Folder
        source_frame = ctk.CTkFrame(control_frame)
        source_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(source_frame, text="Source Folder:").pack(side="left", padx=5)
        self.source_folder_var = ctk.StringVar(value=self.config.source_folders[0] if self.config.source_folders else "")
        ctk.CTkEntry(source_frame, textvariable=self.source_folder_var, width=300).pack(side="left", padx=5)
        ctk.CTkButton(source_frame, text="Browse", command=self.choose_source_folder).pack(side="left", padx=5)
        
        # Action Buttons
        button_frame = ctk.CTkFrame(control_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        self.start_button = ctk.CTkButton(button_frame, text="Start Watching", command=self.start_watching)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ctk.CTkButton(button_frame, text="Stop Watching", command=self.stop_watching, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        self.review_button = ctk.CTkButton(button_frame, text="Review Misclassifications", command=self.open_review)
        self.review_button.pack(side="left", padx=5)
        
        # Tray Toggle
        self.tray_var = ctk.BooleanVar(value=False)
        self.tray_toggle = ctk.CTkSwitch(button_frame, text="Enable Tray Icon", variable=self.tray_var, command=self.toggle_tray)
        self.tray_toggle.pack(side="left", padx=5)
        
        # Progress Bar
        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(button_frame)
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)
        self.progress_bar.set(0)
        
        # Status Label
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(button_frame, textvariable=self.status_var)
        self.status_label.pack(side="left", padx=5)
        
        # Activity Log
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(log_frame, text="Activity Log").pack(anchor="w", padx=5, pady=2)
        
        self.log_text = ctk.CTkTextbox(log_frame, height=200)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Category Stats
        stats_frame = ctk.CTkFrame(main_frame)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(stats_frame, text="Category Statistics").pack(anchor="w", padx=5, pady=2)
        
        self.category_labels = {}
        categories_frame = ctk.CTkFrame(stats_frame)
        categories_frame.pack(fill="x", padx=5, pady=5)
        
        for i, category in enumerate([
            "amateur", "professional", "asian", "european", "american",
            "lesbian", "gay", "trans", "fetish", "bdsm",
            "cosplay", "hentai", "manga", "vintage", "other"
        ]):
            frame = ctk.CTkFrame(categories_frame)
            frame.grid(row=i//3, column=i%3, padx=5, pady=2, sticky="ew")
            
            label = ctk.CTkLabel(frame, text=f"{category.title()}: 0")
            label.pack(side="left", padx=5)
            
            self.category_labels[category] = {
                'label': label,
                'count': 0,
                'increment': 0
            }
            
        categories_frame.grid_columnconfigure((0,1,2), weight=1)

    def create_tray_icon(self):
        """Create system tray icon"""
        def create_icon():
            # Create a simple icon with progress indicator
            size = 64
            image = Image.new('RGB', (size, size), color='black')
            draw = ImageDraw.Draw(image)
            
            # Draw progress circle
            progress = self.stats['progress']
            angle = int(360 * progress / 100)
            draw.arc([(4, 4), (size-4, size-4)], 0, angle, fill='white', width=4)
            
            return image
        
        def on_clicked(icon, item):
            if str(item) == "Show":
                self.root.deiconify()
            elif str(item) == "Exit":
                self.on_closing()
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", on_clicked),
            pystray.MenuItem("Exit", on_clicked)
        )
        
        self.tray_icon = pystray.Icon("OrganizerBot", create_icon(), "OrganizerBot", menu)
        self.tray_icon.run()

    def toggle_tray(self):
        """Toggle system tray icon"""
        if self.tray_var.get():
            if not self.tray_icon:
                threading.Thread(target=self.create_tray_icon, daemon=True).start()
        else:
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None

    def update_stats(self):
        """Update statistics display"""
        # Update progress bar
        self.progress_bar.set(self.stats['progress'] / 100)
        
        # Update category counts with increments
        for category, data in self.category_labels.items():
            if data['increment'] > 0:
                data['label'].configure(text=f"{category.title()}: {data['count']} (+{data['increment']})", text_color="green")
                data['increment'] = 0
            else:
                data['label'].configure(text=f"{category.title()}: {data['count']}", text_color="white")
        
        # Schedule next update
        self.root.after(1000, self.update_stats)

    def update_log(self):
        """Update the log display with new messages"""
        try:
            while True:
                message = gui_queue.get_nowait()
                self.log_text.insert("end", f"{message}\n")
                self.log_text.see("end")
                
                # Update stats based on message content
                if "Processing file:" in message:
                    self.stats['total_processed'] += 1
                    self.stats['last_processed'] = message.split("Processing file:")[1].strip()
                    self.stats['progress'] = min(100, self.stats['progress'] + 1)
                elif "Image categorized as:" in message:
                    category = message.split("Image categorized as:")[1].strip()
                    self.stats['category_counts'][category] += 1
                    if category in self.category_labels:
                        self.category_labels[category]['count'] += 1
                        self.category_labels[category]['increment'] += 1
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_log)

    def start_watching(self):
        """Start the file watcher"""
        if not self.watcher_thread or not self.watcher_thread.is_alive():
            if not os.path.exists(self.config.watch_folder):
                messagebox.showerror("Error", "Watch folder does not exist!")
                return
            if not self.config.source_folders:
                messagebox.showerror("Error", "Please set a source folder first!")
                return
            
            from watchdog.observers import Observer
            event_handler = FileEventHandler(self.config)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.config.watch_folder, recursive=True)
            self.observer.start()
            
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_var.set("Watching...")
            self.log_message("Started watching folder: " + self.config.watch_folder)
            
            # Start initial scan
            self.manual_refresh()

    def stop_watching(self):
        """Stop the file watcher"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.status_var.set("Stopped")
            self.log_message("Stopped watching folder")

    def manual_refresh(self):
        """Manually process files in watch folder"""
        if not os.path.exists(self.config.watch_folder):
            messagebox.showerror("Error", "Watch folder does not exist!")
            return
        if not self.config.source_folders:
            messagebox.showerror("Error", "Please set a source folder first!")
            return
            
        self.log_message("Scanning folder...")
        
        # Process all files in watch folder
        for filename in os.listdir(self.config.watch_folder):
            file_path = os.path.join(self.config.watch_folder, filename)
            if os.path.isfile(file_path):
                event = type('Event', (), {'is_directory': False, 'src_path': file_path})()
                handler = FileEventHandler(self.config)
                handler.on_modified(event)
        
        self.log_message("Scan completed!")

    def load_config(self):
        """Load configuration into UI"""
        # Load watch folder
        self.watch_folder_var.set(self.config.watch_folder)
        
        # Load source folder
        if self.config.source_folders:
            self.source_folder_var.set(self.config.source_folders[0])
        
        # Log initial state
        self.log_message("Configuration loaded")
        if self.config.watch_folder:
            self.log_message(f"Watch folder: {self.config.watch_folder}")
        if self.config.source_folders:
            self.log_message(f"Source folder: {self.config.source_folders[0]}")

    def choose_watch_folder(self):
        """Open folder selection dialog for watch folder"""
        folder = filedialog.askdirectory()
        if folder:
            self.watch_folder_var.set(folder)
            self.config.watch_folder = folder
            self.save_settings()

    def choose_source_folder(self):
        """Open folder selection dialog for source folder"""
        folder = filedialog.askdirectory()
        if folder:
            self.source_folder_var.set(folder)
            self.config.source_folders = [folder]
            self.save_settings()

    def save_settings(self):
        """Save current settings"""
        self.config.watch_folder = self.watch_folder_var.get()
        self.config.source_folders = [self.source_folder_var.get()] if self.source_folder_var.get() else []
        save_config(self.config)
        self.log_message("Settings saved successfully!")

    def log_message(self, message: str):
        """Add a message to the log"""
        log_action(message)  # This will also update the GUI through the queue

    def on_closing(self):
        """Handle window closing"""
        if self.observer:
            self.stop_watching()
        self.root.destroy()

    def open_review(self):
        """Open review window"""
        if not self.review_window:
            self.review_window = ReviewWindow(self.root)
        self.review_window.show()

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def run_gui():
    """Start the GUI"""
    window = MainWindow()
    window.run() 