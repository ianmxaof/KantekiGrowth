"""
Review window for correcting misclassifications
"""
import tkinter as tk
from tkinter import ttk
import json
from PIL import Image, ImageTk
import os
from typing import Dict, List, Optional
from organizerbot.processors.self_trainer import SelfTrainer
from organizerbot.utils.logger import log_action

class ReviewWindow:
    def __init__(self, parent, log_path: str = "misclass_log.json"):
        self.window = tk.Toplevel(parent)
        self.window.title("Review Misclassifications")
        self.window.geometry("1200x800")
        
        self.log_path = log_path
        self.trainer = SelfTrainer(log_path)
        self.current_index = 0
        self.entries = self._load_entries()
        
        self._create_widgets()
        self._load_current_entry()
        
    def _create_widgets(self):
        """Create GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Image display
        self.image_label = ttk.Label(main_frame)
        self.image_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # Metadata display
        meta_frame = ttk.LabelFrame(main_frame, text="Image Metadata", padding="5")
        meta_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.meta_text = tk.Text(meta_frame, height=6, width=80)
        self.meta_text.grid(row=0, column=0, padx=5, pady=5)
        
        # Category selection
        cat_frame = ttk.LabelFrame(main_frame, text="Select Correct Category", padding="5")
        cat_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(cat_frame, textvariable=self.cat_var)
        self.cat_combo['values'] = list(self.trainer.CATEGORY_PROMPTS.keys())
        self.cat_combo.grid(row=0, column=0, padx=5, pady=5)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(nav_frame, text="Previous", command=self._prev_entry).grid(row=0, column=0, padx=5)
        ttk.Button(nav_frame, text="Next", command=self._next_entry).grid(row=0, column=1, padx=5)
        ttk.Button(nav_frame, text="Save & Train", command=self._save_and_train).grid(row=0, column=2, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_bar.grid(row=4, column=0, columnspan=2, sticky="ew")
        
        # Configure grid weights
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
    def _load_entries(self) -> List[Dict]:
        """Load misclassification entries"""
        try:
            with open(self.log_path) as f:
                return json.load(f)
        except Exception as e:
            log_action(f"Error loading entries: {str(e)}")
            return []
            
    def _load_current_entry(self):
        """Load current entry data"""
        if not self.entries:
            self.status_var.set("No entries to review")
            return
            
        entry = self.entries[self.current_index]
        
        # Load and display image
        try:
            img = Image.open(entry["image_path"])
            img.thumbnail((800, 600))
            photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=photo)
            self.image_label.image = photo
        except Exception as e:
            log_action(f"Error loading image: {str(e)}")
            self.image_label.configure(text="Error loading image")
            
        # Display metadata
        meta_text = f"Path: {entry['image_path']}\n"
        meta_text += f"Timestamp: {entry['timestamp']}\n"
        meta_text += f"Faces detected: {entry['faces_detected']}\n"
        meta_text += f"CLIP confidence: {entry['clip_confidence']:.2f}%\n"
        meta_text += f"Top prompt: {entry['top_prompt']}\n"
        
        for feature, value in entry.items():
            if isinstance(value, bool):
                meta_text += f"{feature}: {value}\n"
                
        self.meta_text.delete(1.0, tk.END)
        self.meta_text.insert(tk.END, meta_text)
        
        # Set current category
        if "correct_label" in entry:
            self.cat_var.set(entry["correct_label"])
        else:
            self.cat_var.set("")
            
        # Update status
        self.status_var.set(f"Entry {self.current_index + 1} of {len(self.entries)}")
        
    def _prev_entry(self):
        """Load previous entry"""
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_entry()
            
    def _next_entry(self):
        """Load next entry"""
        if self.current_index < len(self.entries) - 1:
            self.current_index += 1
            self._load_current_entry()
            
    def _save_and_train(self):
        """Save corrections and retrain model"""
        if not self.entries:
            return
            
        # Save correction
        entry = self.entries[self.current_index]
        entry["correct_label"] = self.cat_var.get()
        
        with open(self.log_path, 'w') as f:
            json.dump(self.entries, f, indent=2)
            
        # Retrain model
        self.trainer.train_classifier()
        
        # Update status
        self.status_var.set("Corrections saved and model retrained")
        
    def show(self):
        """Show the review window"""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force() 