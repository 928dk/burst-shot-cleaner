import os
import shutil
import time
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog # Import filedialog
import customtkinter as ctk
from PIL import Image
import pandas as pd
import threading
import json # Import the json module

# Configuration
CTK_THEME = "dark-blue"
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme(CTK_THEME)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}

# Configuration file path
CONFIG_DIR = Path.home() / ".config" / "burst-shot-cleaner"
CONFIG_FILE = CONFIG_DIR / "config.json"

class BurstShotCleaner(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Burst Shot Cleaner v1.3.0") # Version update
        self.geometry("1100x800")

        # Variables
        self.scan_dirs = [] 
        self.burst_groups_data = [] 
        self.files_to_move = []
        self.is_scanning = False
        self.is_cleaning = False
        self.dry_run_var = tk.BooleanVar(value=True)
        self.thumbnails = []
        self.images_to_keep_var = tk.IntVar(value=3) 
        self.burst_timeframe_var = tk.DoubleVar(value=5.0) 
        self.sort_by_var = tk.StringVar(value="mtime") # Default sort order: modification time

        self._setup_ui()
        self.load_preferences() # Load preferences on startup
        self.update_selected_dirs_label() # Update label to reflect loaded dirs

    def load_preferences(self):
        try:
            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    prefs = json.load(f)
                
                # Set Tkinter variables
                self.images_to_keep_var.set(prefs.get("images_to_keep", 3))
                self.burst_timeframe_var.set(prefs.get("burst_timeframe", 5.0))
                self.sort_by_var.set(prefs.get("sort_by", "mtime"))
                self.scan_dirs = prefs.get("scan_dirs", [])
                
                status_msg = "Preferences loaded."
                if not self.scan_dirs:
                    status_msg = "Preferences loaded. No directories selected. Please add directories."
                self.status_label.configure(text=status_msg)
            else:
                # No config file, use defaults. Status message is already set in __init__.
                pass
                
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading preferences: {e}")
            self.status_label.configure(text="Error loading preferences. Using defaults.")
            # Reset to defaults on error to ensure a clean state
            self.images_to_keep_var.set(3)
            self.burst_timeframe_var.set(5.0)
            self.sort_by_var.set("mtime")
            self.scan_dirs = []
        
        # Bind trace to variables to save preferences when they change
        # This must be done *after* loading to avoid saving defaults immediately on load
        self.images_to_keep_var.trace_add("write", lambda *args: self.save_preferences())
        self.burst_timeframe_var.trace_add("write", lambda *args: self.save_preferences())
        self.sort_by_var.trace_add("write", lambda *args: self.save_preferences())
        # scan_dirs changes are handled by add_scan_directory

    def save_preferences(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            prefs = {
                "images_to_keep": self.images_to_keep_var.get(),
                "burst_timeframe": self.burst_timeframe_var.get(),
                "sort_by": self.sort_by_var.get(),
                "scan_dirs": self.scan_dirs
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(prefs, f, indent=4)
        except OSError as e:
            print(f"Error saving preferences: {e}")
            self.status_label.configure(text="Error saving preferences.")

    def update_selected_dirs_label(self):
        if not self.scan_dirs:
            self.selected_dirs_label.configure(text="Selected: None")
        else:
            basenames = [os.path.basename(d) for d in self.scan_dirs]
            display_text = "Selected: " + ", ".join(basenames)
            # Basic shortening to avoid overflowing the label
            if len(display_text) > 30:
                display_text = ", ".join([os.path.basename(d)[:10] + "..." for d in self.scan_dirs[:2]])
                if len(self.scan_dirs) > 2: display_text += ", ..."
                if len(display_text) > 30: display_text = "Selected: Too many/long"
            self.selected_dirs_label.configure(text=display_text)

    def add_scan_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            if directory not in self.scan_dirs:
                self.scan_dirs.append(directory)
                self.update_selected_dirs_label()
                self.status_label.configure(text="Directory added. Press Scan to process.")
                self.save_preferences() # Save after adding directory
            else:
                # Optionally show a message if directory already exists
                pass
                
    def update_sort_preference(self, selected_value):
        # `selected_value` is the displayed text ("Modified", "Filename")
        if selected_value == "Modified":
            self.sort_by_var.set("mtime")
        elif selected_value == "Filename":
            self.sort_by_var.set("name")
        # The trace_add on self.sort_by_var will automatically call save_preferences

    def start_scan(self):
        if self.is_scanning: return
        if not self.scan_dirs:
            self.status_label.configure(text="Please select a directory first.")
            return

        self.is_scanning = True
        self.status_label.configure(text="Scanning...")
        for widget in self.groups_frame.winfo_children(): widget.destroy()
        self.preview_frame.destroy() # Recreate preview frame to clear it
        self.preview_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Image Previews", height=200)
        self.preview_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0) # Reset progress bar
        self.cleanup_btn.configure(state="disabled") # Disable cleanup button during scan
        self.scan_btn.configure(state="disabled") # Disable scan button during scan

        thread = threading.Thread(target=self.scan_task); thread.daemon = True; thread.start()

    def scan_task(self):
        all_files = []
        for d in self.scan_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        p = Path(os.path.join(root, f))
                        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                            try:
                                stat = p.stat()
                                all_files.append({"path": p, "mtime": stat.st_mtime, "size": stat.st_size, "name": p.name})
                            except OSError: # Handle potential permission errors etc.
                                continue

        if not all_files:
            self.after(0, lambda: self.finish_scan([], []))
            return

        # Create DataFrame first, then sort based on user preference
        df = pd.DataFrame(all_files) 

        # Apply sorting based on user preference
        sort_key = self.sort_by_var.get()
        if sort_key == "name":
            df = df.sort_values("name").reset_index(drop=True)
        else: # Default to mtime
            df = df.sort_values("mtime").reset_index(drop=True)
        
        processed_groups_data = []
        all_files_to_move = []

        # Get images to keep from UI
        try:
            k = self.images_to_keep_var.get()
            if k < 1: k = 1 # Ensure at least 1 image is kept
        except tk.TclError: # Handle invalid input (e.g., non-numeric)
            k = 3 # Default to 3 if input is invalid
            
        # Get burst timeframe from UI
        try:
            burst_threshold = self.burst_timeframe_var.get()
            if burst_threshold < 0.1: burst_threshold = 0.1 # Minimum threshold to avoid grouping everything
        except tk.TclError: # Handle invalid input
            burst_threshold = 5.0 # Default to 5.0 seconds

        if not df.empty:
            current_group_indices = []
            if not df.empty:
                current_group_indices = [0]
                for i in range(1, len(df)):
                    # Use the dynamic burst_threshold here
                    if df.iloc[i]["mtime"] - df.iloc[i-1]["mtime"] <= burst_threshold:
                        current_group_indices.append(i)
                    else:
                        if len(current_group_indices) > 1:
                            group_df = df.iloc[current_group_indices]
                            n = len(group_df)
                            
                            indices_to_keep = set()
                            if k >= n:
                                indices_to_keep = set(range(n)) # Keep all if k is >= total images in burst
                            else:
                                # Keep the first k images
                                indices_to_keep = set(range(k))

                            files_to_move_in_group = [
                                group_df.iloc[idx].to_dict() 
                                for idx in range(n) 
                                if idx not in indices_to_keep
                            ]
                            
                            processed_groups_data.append({"df": group_df, "to_move": files_to_move_in_group, "num_kept": len(indices_to_keep)})
                            all_files_to_move.extend(files_to_move_in_group) # Aggregate files to move

                        current_group_indices = [i]
                
                # Process the last group if it exists and has more than 1 image
                if len(current_group_indices) > 1:
                    group_df = df.iloc[current_group_indices]
                    n = len(group_df)

                    indices_to_keep = set()
                    if k >= n:
                        indices_to_keep = set(range(n))
                    else:
                        indices_to_keep = set(range(k))

                    files_to_move_in_group = [
                        group_df.iloc[idx].to_dict() 
                        for idx in range(n) 
                        if idx not in indices_to_keep
                    ]
                    processed_groups_data.append({"df": group_df, "to_move": files_to_move_in_group, "num_kept": len(indices_to_keep)})
                    all_files_to_move.extend(files_to_move_in_group)

        self.after(0, lambda: self.finish_scan(processed_groups_data, all_files_to_move))

    def finish_scan(self, burst_groups_data, to_move):
        self.is_scanning = False
        self.files_to_move = to_move
        self.burst_groups_data = burst_groups_data # Store for preview display
        
        status_text = f"Scan complete. Found {len(to_move)} redundant photos."
        if not self.scan_dirs: status_text = "No directories selected for scanning. Please add directories."
        elif not to_move: status_text = "Scan complete. No redundant photos found."
        self.status_label.configure(text=status_text)

        if to_move: self.cleanup_btn.configure(state="normal")
        
        # Sort the groups by the number of images in descending order
        sorted_groups_data = sorted(burst_groups_data, key=lambda group: len(group['df']), reverse=True)
        
        # Clear existing groups
        for widget in self.groups_frame.winfo_children(): widget.destroy()
        
        # Iterate through sorted groups to display them
        for i, group_data in enumerate(sorted_groups_data): # Use sorted_groups_data
            group_df = group_data["df"]
            num_images_in_group = len(group_df)
            num_to_keep = group_data["num_kept"] # Use stored value
            
            row = ctk.CTkFrame(self.groups_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            lbl_text = f"Group {i+1}: {num_images_in_group} images ({num_to_keep} to keep)"
            lbl = ctk.CTkLabel(row, text=lbl_text, width=200, anchor="w")
            lbl.pack(side="left", padx=10)
            
            btn = ctk.CTkButton(row, text="View", width=60, height=20, command=lambda g=group_df: self.show_previews(g))
            btn.pack(side="right", padx=10)

        # Re-enable scan button after scan is finished.
        self.scan_btn.configure(state="normal")


    def show_previews(self, group_df):
        for widget in self.preview_frame.winfo_children(): widget.destroy()
        self.thumbnails = []

        # Get the current number of images to keep from the UI
        try:
            k = self.images_to_keep_var.get()
            if k < 1: k = 1
        except tk.TclError:
            k = 3 # Default

        n = len(group_df)
        
        indices_to_keep = set()
        if k >= n:
            indices_to_keep = set(range(n))
        else:
            indices_to_keep = set(range(k)) # Keep the first k images

        for idx, (_, row) in enumerate(group_df.iterrows()):
            try:
                pil_img = Image.open(str(row['path']))
                pil_img.thumbnail((150, 150))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 150))
                
                frame_border_color = ("gray80", "gray40") # Default border for files to move
                if idx in indices_to_keep:
                    frame_border_color = ("green4", "green4") # Highlight kept images

                # Create a container frame for each preview item (image + filename)
                item_container_frame = ctk.CTkFrame(self.preview_frame, corner_radius=5, border_width=2, 
                                                     border_color=frame_border_color)
                item_container_frame.pack(side="left", padx=5, pady=5)

                # Image label within the container
                img_label = ctk.CTkLabel(item_container_frame, image=ctk_img, text="")
                img_label.pack()

                # Filename label below the image
                filename_label = ctk.CTkLabel(item_container_frame, text=row['name'], font=ctk.CTkFont(size=10))
                filename_label.pack()

                self.thumbnails.append(ctk_img)
            except Exception as e:
                print(f"Error loading preview for {row['path']}: {e}")
                # Optionally show a placeholder for images that failed to load
                pass

    def start_cleanup(self):
        if self.is_cleaning: return
        if not self.files_to_move:
            self.status_label.configure(text="No files selected for cleanup.")
            return
            
        self.is_cleaning = True
        self.status_label.configure(text="Archiving...")
        self.cleanup_btn.configure(state="disabled") # Disable button during cleanup
        self.scan_btn.configure(state="disabled") # Disable scan button during cleanup
        thread = threading.Thread(target=self.cleanup_task); thread.daemon = True; thread.start()

    def cleanup_task(self):
        is_dry = self.dry_run_var.get()
        archive_dir_base = Path("$HOME/Pictures/cleanup_archive")
        
        if not is_dry:
            try:
                # Create a timestamped directory for this cleanup session
                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_dir = archive_dir_base / timestamp_str
                archive_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                self.after(0, lambda: self.status_label.configure(text=f"Error creating archive directory: {e}"))
                self.is_cleaning = False
                self.cleanup_btn.configure(state="normal")
                self.scan_btn.configure(state="normal")
                return

        total_files = len(self.files_to_move)
        if total_files == 0:
            self.after(0, lambda: self.status_label.configure(text="No files to clean."))
            self.is_cleaning = False
            self.cleanup_btn.configure(state="normal")
            self.scan_btn.configure(state="normal")
            return

        for i, item in enumerate(self.files_to_move):
            try:
                source_path = Path(item["path"])
                if not is_dry:
                    # Ensure the target directory exists before moving
                    if not is_dry: shutil.move(str(source_path), str(archive_dir / source_path.name))
                
                # Update progress bar on the main thread
                progress = (i + 1) / total_files
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                
            except Exception as e:
                print(f"Error processing file {item['path']}: {e}")
                # Optionally update status label with error, or log it
                # Continue with next file

        self.after(0, self.finish_cleanup)

    def finish_cleanup(self):
        self.is_cleaning = False
        if self.dry_run_var.get():
            self.status_label.configure(text="Dry Run complete. No files were moved.")
        else:
            self.status_label.configure(text="Cleanup complete! Check cleanup_archive.")
        self.progress_bar.set(0) # Reset progress bar
        self.cleanup_btn.configure(state="normal") # Re-enable button
        self.scan_btn.configure(state="normal") # Re-enable scan button


if __name__ == "__main__":
    app = BurstShotCleaner()
    app.mainloop()
