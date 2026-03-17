#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from flask import Flask
import threading
import socket
import datetime
import keyboard
import logging
import platform
import subprocess
from pathlib import Path

# Configure logging for debugging (macOS specific path)
log_dir = os.path.expanduser('~/Library/Logs/SignalReceiver')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

# Also log to console for debugging
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

PORT = 5000
app = Flask(__name__)

# Key mappings
forward_keys = ""           # default
revert_keys = ""  # default: press twice

log_callback = None

# Check if running as app or script
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def log(message):
    if log_callback:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        log_callback(log_entry)
        logging.info(message)
    else:
        logging.info(f"No callback: {message}")

@app.route("/trigger")
def trigger():
    log(f"Forward signal received → press {forward_keys}")
    try:
        if forward_keys:
            keys = [k.strip() for k in forward_keys.split(",") if k.strip()]
            for k in keys:
                keyboard.send(k)
                logging.info(f"Sent key: {k}")
        else:
            log("No forward keys configured")
    except Exception as e:
        error_msg = f"Failed to press keys: {e}"
        log(error_msg)
        logging.error(error_msg, exc_info=True)
    return "OK"

@app.route("/revert")
def revert():
    log(f"Revert signal received → press {revert_keys}")
    try:
        if revert_keys:
            keys = [k.strip() for k in revert_keys.split(",") if k.strip()]
            for k in keys:
                keyboard.send(k)
                logging.info(f"Sent key: {k}")
        else:
            log("No revert keys configured")
    except Exception as e:
        error_msg = f"Failed to press keys: {e}"
        log(error_msg)
        logging.error(error_msg, exc_info=True)
    return "OK"

def run_server():
    """Run Flask server in a separate thread"""
    try:
        logging.info(f"Starting Flask server on port {PORT}")
        app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        error_msg = f"Flask server failed: {e}"
        logging.error(error_msg, exc_info=True)
        log(error_msg)

def get_local_ip():
    """Get local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        logging.info(f"Detected IP: {ip}")
    except Exception as e:
        ip = "Unavailable"
        logging.error(f"Failed to get IP: {e}")
    finally:
        s.close()
    return ip

def check_permissions():
    """Check if accessibility permissions are granted (macOS specific)"""
    if platform.system() == 'Darwin':  # macOS
        try:
            # Try to use keyboard to check permissions
            import keyboard
            # This will trigger permission dialog if needed
            keyboard.is_pressed('shift')
            return True
        except Exception as e:
            logging.error(f"Permission check failed: {e}")
            return False
    return True

def request_permissions():
    """Show instructions for granting permissions (macOS specific)"""
    if platform.system() == 'Darwin' and not check_permissions():
        msg = (
            "Signal Receiver needs Accessibility permissions to control keyboard.\n\n"
            "Please grant permission:\n"
            "1. Open System Settings\n"
            "2. Go to Privacy & Security → Accessibility\n"
            "3. Click '+' and add Signal Receiver\n"
            "4. Restart the app"
        )
        messagebox.showwarning("Permissions Required", msg)
        logging.warning("User shown permission instructions")
        return False
    return True

def save_config():
    """Save key mappings to config file"""
    config_dir = os.path.expanduser('~/Library/Application Support/SignalReceiver')
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, 'config.txt')
    
    try:
        with open(config_file, 'w') as f:
            f.write(f"forward={forward_keys}\n")
            f.write(f"revert={revert_keys}\n")
        logging.info(f"Config saved to {config_file}")
    except Exception as e:
        logging.error(f"Failed to save config: {e}")

def load_config():
    """Load key mappings from config file"""
    global forward_keys, revert_keys
    config_file = os.path.expanduser('~/Library/Application Support/SignalReceiver/config.txt')
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if line.startswith('forward='):
                        forward_keys = line.strip()[8:]
                    elif line.startswith('revert='):
                        revert_keys = line.strip()[7:]
            logging.info(f"Config loaded from {config_file}")
            return True
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
    return False

# -------------------------
# Tkinter UI
# -------------------------
def create_ui():
    global root, forward_label, revert_label, log_box, status_label, forward_keys, revert_keys
    
    root = tk.Tk()
    root.title("BAYA ARTS - Receiver")
    
    # Set window size and position
    window_width = 500
    window_height = 500
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)
    
    # Set app icon if available
    try:
        icon_path = resource_path('icon.icns')
        if platform.system() == 'Darwin' and os.path.exists(icon_path):
            root.iconbitmap(default=icon_path)
    except:
        pass
    
    # Main container
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Title
    title = tk.Label(
        main_frame, 
        text="Signal Receiver", 
        font=("Helvetica", 18, "bold")
    )
    title.pack(pady=(0, 15))
    
    # Network info
    ip_address = get_local_ip()
    info_frame = tk.LabelFrame(
        main_frame, 
        text="Network Information", 
        padx=15, 
        pady=10,
        font=("Helvetica", 10, "bold")
    )
    info_frame.pack(fill="x", pady=10)
    
    ip_label = tk.Label(
        info_frame, 
        text=f"IP Address: {ip_address}", 
        font=("Helvetica", 11)
    )
    ip_label.pack(anchor="w")
    
    port_label = tk.Label(
        info_frame, 
        text=f"Port: {PORT}", 
        font=("Helvetica", 11)
    )
    port_label.pack(anchor="w")
    
    # System info for macOS
    if platform.system() == 'Darwin':
        system_label = tk.Label(
            info_frame,
            text="System: macOS",
            font=("Helvetica", 10),
            fg="gray"
        )
        system_label.pack(anchor="w")
    
    # Key mapping panel
    mapping_frame = tk.LabelFrame(
        main_frame, 
        text="Key Mapping", 
        padx=15, 
        pady=10,
        font=("Helvetica", 10, "bold")
    )
    mapping_frame.pack(fill="x", pady=10)
    
    # Forward keys row
    forward_row = tk.Frame(mapping_frame)
    forward_row.pack(fill="x", pady=5)
    
    forward_btn = tk.Button(
        forward_row, 
        text="Set Forward Keys", 
        command=set_forward_keys,
        bg="#4CAF50",
        fg="white",
        padx=10,
        cursor="hand2"
    )
    forward_btn.pack(side="left", padx=5)
    
    forward_label = tk.Label(
        forward_row, 
        text=f"Forward: {forward_keys or 'Not set'}",
        font=("Helvetica", 10),
        wraplength=200
    )
    forward_label.pack(side="left", padx=10)
    
    # Revert keys row
    revert_row = tk.Frame(mapping_frame)
    revert_row.pack(fill="x", pady=5)
    
    revert_btn = tk.Button(
        revert_row, 
        text="Set Revert Keys", 
        command=set_revert_keys,
        bg="#f44336",
        fg="white",
        padx=10,
        cursor="hand2"
    )
    revert_btn.pack(side="left", padx=5)
    
    revert_label = tk.Label(
        revert_row, 
        text=f"Revert: {revert_keys or 'Not set'}",
        font=("Helvetica", 10),
        wraplength=200
    )
    revert_label.pack(side="left", padx=10)
    
    # Log panel
    log_frame = tk.LabelFrame(
        main_frame, 
        text="Signal Log", 
        padx=15, 
        pady=10,
        font=("Helvetica", 10, "bold")
    )
    log_frame.pack(fill="both", expand=True, pady=10)
    
    log_box = scrolledtext.ScrolledText(
        log_frame, 
        height=10, 
        state="disabled",
        font=("Courier", 9),
        wrap=tk.WORD
    )
    log_box.pack(fill="both", expand=True)
    
    # Clear log button
    clear_btn = tk.Button(
        log_frame,
        text="Clear Log",
        command=clear_log,
        cursor="hand2"
    )
    clear_btn.pack(pady=5)
    
    # Status bar
    status_frame = tk.Frame(main_frame)
    status_frame.pack(fill="x", pady=5)
    
    status_label = tk.Label(
        status_frame, 
        text="Initializing...", 
        font=("Helvetica", 10),
        fg="blue"
    )
    status_label.pack(side="left")
    
    # Version info
    version_label = tk.Label(
        status_frame,
        text="v1.0.0",
        font=("Helvetica", 8),
        fg="gray"
    )
    version_label.pack(side="right")
    
    return root

def set_forward_keys():
    global forward_keys, forward_label
    dialog = CustomDialog(
        root,
        "Forward Keys",
        "Enter keys to press for forward signal:\nExamples: space, ctrl+shift+a, cmd+space\nSeparate multiple with commas",
        forward_keys
    )
    result = dialog.show()
    if result is not None:
        forward_keys = result
        forward_label.config(text=f"Forward: {forward_keys or 'Not set'}")
        log(f"Forward keys set to: {forward_keys}")
        save_config()
        logging.info(f"Forward keys updated: {forward_keys}")

def set_revert_keys():
    global revert_keys, revert_label
    dialog = CustomDialog(
        root,
        "Revert Keys",
        "Enter keys to press for revert signal:\nExamples: space, ctrl+shift+a, cmd+space\nSeparate multiple with commas",
        revert_keys
    )
    result = dialog.show()
    if result is not None:
        revert_keys = result
        revert_label.config(text=f"Revert: {revert_keys or 'Not set'}")
        log(f"Revert keys set to: {revert_keys}")
        save_config()
        logging.info(f"Revert keys updated: {revert_keys}")

def clear_log():
    """Clear the log display"""
    log_box.config(state="normal")
    log_box.delete(1.0, tk.END)
    log_box.config(state="disabled")
    logging.info("Log cleared by user")

def append_log(text):
    """Add text to log display"""
    try:
        log_box.config(state="normal")
        log_box.insert(tk.END, text + "\n")
        log_box.see(tk.END)
        log_box.config(state="disabled")
    except Exception as e:
        logging.error(f"Failed to update log display: {e}")

class CustomDialog:
    """Custom dialog for key input"""
    def __init__(self, parent, title, message, default=""):
        self.parent = parent
        self.title = title
        self.message = message
        self.default = default
        self.result = None
        
    def show(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        width = 400
        height = 200
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Message
        msg_label = tk.Label(dialog, text=self.message, wraplength=350, justify=tk.LEFT)
        msg_label.pack(pady=10, padx=10)
        
        # Entry
        entry_var = tk.StringVar(value=self.default)
        entry = tk.Entry(dialog, textvariable=entry_var, width=40)
        entry.pack(pady=10, padx=10)
        entry.select_range(0, tk.END)
        entry.focus()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_ok():
            self.result = entry_var.get().strip()
            dialog.destroy()
            
        def on_cancel():
            dialog.destroy()
        
        ok_btn = tk.Button(button_frame, text="OK", command=on_ok, width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Wait for dialog to close
        self.parent.wait_window(dialog)
        return self.result

def on_closing():
    """Handle window close event"""
    logging.info("Application shutting down")
    save_config()
    root.destroy()
    sys.exit(0)

# Main execution
if __name__ == "__main__":
    try:
        logging.info("=" * 50)
        logging.info("Signal Receiver starting...")
        logging.info(f"Platform: {platform.system()} {platform.release()}")
        logging.info(f"Python: {sys.version}")
        
        # Load saved config
        load_config()
        
        # Check macOS permissions
        if platform.system() == 'Darwin':
            request_permissions()
        
        # Create UI
        root = create_ui()
        
        # Set up log callback
        log_callback = append_log
        
        # Start Flask server in thread
        try:
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            logging.info("Server thread started")
            status_label.config(text="✓ Server running", fg="green")
            log("Server started successfully")
        except Exception as e:
            error_msg = f"Failed to start server: {e}"
            logging.error(error_msg, exc_info=True)
            status_label.config(text="✗ Server failed to start", fg="red")
            log(error_msg)
            messagebox.showerror("Server Error", f"Failed to start server:\n{e}")
        
        # Handle window close
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start main loop
        logging.info("UI starting")
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", 
            f"Application failed to start:\n{e}\n\nCheck logs at:\n~/Library/Logs/SignalReceiver/app.log")
        sys.exit(1)