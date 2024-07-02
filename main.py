import os
import pickle
import threading
import time
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import logging
from pynput import mouse
import keyboard as hotkey
import random

class MacroMaker:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-topmost', True)
        self.frm = ttk.Frame(root, padding=10)

        self.logger = logging.getLogger(__name__)

        self.recording = False
        self.loop = False
        self.running = False
        self.macro_data = []
        self.macros = {}

        self.delay_min = 2  # Default minimum delay
        self.delay_max = 4  # Default maximum delay
        self.x_offset = 15  # Default X offset
        self.y_offset = 15  # Default Y offset
        self.use_custom_delays_offsets = False  # Toggle for using custom delays and offsets

        self.listener_mouse = mouse.Listener(on_click=self.on_click)
        self.listener_mouse.start()

        self.frm.grid()

        # Menu bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=self.options_menu)
        self.options_menu.add_command(label="Toggle Loop", command=self.toggle_loop)
        self.options_menu.add_command(label="Settings", command=self.open_settings)

        ### Top Row ###
        self.record_button = ttk.Button(self.frm, text="Record", command=self.record_macro)
        self.record_button.grid(column=0, row=0, padx=5, pady=10)
        self.stop_button = ttk.Button(self.frm, text="Stop", command=self.stop_macro)
        self.stop_button.grid(column=2, row=0, padx=5, pady=10)
        self.play_button = ttk.Button(self.frm, text="Play", command=self.play_macro)
        self.play_button.grid(column=3, row=0, padx=5, pady=10)
        self.delete_button = ttk.Button(self.frm, text="Delete", command=self.delete_macro)
        self.delete_button.grid(column=4, row=0, padx=5, pady=10)
        self.rename_button = ttk.Button(self.frm, text="Rename", command=self.rename_macro)
        self.rename_button.grid(column=5, row=0, padx=5, pady=10)

        ### Second Row ###
        self.macro_list = tk.Listbox(root)
        self.macro_list.grid(column=0, row=1, columnspan=5, padx=5, pady=5, sticky='nsew')

        ### Loop Status ###
        self.loop_status = tk.Label(root, text="Looping: OFF", fg="red")
        self.loop_status.grid(column=0, row=2, columnspan=5, padx=5, pady=5)

        self.running_status = tk.Label(root, text="Status: Not running", fg="red")
        self.running_status.grid(column=0, row=3, columnspan=5, padx=5, pady=5)

        self.load_macros()

        hotkey.add_hotkey("ctrl+shift+r", self.record_macro)
        hotkey.add_hotkey("ctrl+shift+s", self.stop_macro)
        hotkey.add_hotkey("ctrl+shift+x", self.toggle_loop)

        self.record_button.update_idletasks()
        self.button_coords = {
            "record": self.get_button_coordinates(self.record_button),
            "stop": self.get_button_coordinates(self.stop_button),
            "play": self.get_button_coordinates(self.play_button),
            "delete": self.get_button_coordinates(self.delete_button),
            "rename": self.get_button_coordinates(self.rename_button)
        }

    def get_button_coordinates(self, button):
        x_root, y_root = button.winfo_rootx(), button.winfo_rooty()
        width, height = button.winfo_width(), button.winfo_height()
        return (x_root, y_root, x_root + width, y_root + height)

    def is_click_within_button(self, x, y):
        for coords in self.button_coords.values():
            x1, y1, x2, y2 = coords
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        return False

    def record_macro(self):
        if self.recording:
            self.logger.warning("Already recording")
            return

        self.recording = True
        self.macro_data = []
        self.start_time = time.time()
        self.logger.warning("Recording started")

    def on_click(self, x, y, button, pressed):
        if not self.recording or not pressed:
            return

        if self.is_click_within_button(x, y):
            self.logger.warning(f"Click on button ignored: {button}")
            return

        action_time = time.time()
        action = ('click', (x, y), button)
        self.logger.warning(f'Mouse click at x: {x}, y: {y}')
        self.macro_data.append((action, action_time))

    def stop_macro(self):
        if not self.recording:
            return

        self.recording = False
        self.logger.warning("Recording stopped")
        self.root.after(0, self.save_macro_dialog)

    def save_macro_dialog(self):
        macro_name = simpledialog.askstring("Save Macro", "Enter macro name:")
        if macro_name:
            self.macros[macro_name] = self.macro_data
            self.save_macros()
            self.update_macro_list()

    def update_macro_list(self):
        self.macro_list.delete(0, tk.END)
        for macro_name in self.macros:
            self.macro_list.insert(tk.END, macro_name)

    def save_macros(self):
        with open('macros.pkl', 'wb') as f:
            pickle.dump(self.macros, f)

    def load_macros(self):
        if os.path.exists('macros.pkl'):
            with open('macros.pkl', 'rb') as f:
                self.macros = pickle.load(f)
            self.update_macro_list()

    def rename_macro(self):
        selected_macro = self.get_selected_macro()
        if not selected_macro:
            return

        new_name = simpledialog.askstring("Rename Macro", "Enter new macro name:")
        if new_name:
            self.macros[new_name] = self.macros.pop(selected_macro)
            self.save_macros()
            self.update_macro_list()

    def play_macro(self):
        selected_macro = self.get_selected_macro()
        if not selected_macro:
            return

        # Run playback in a separate thread
        threading.Thread(target=self._play_macro_thread, args=(selected_macro,)).start()

    def get_selected_macro(self):
        selected_indices = self.macro_list.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "No macro selected.")
            return None

        return self.macro_list.get(selected_indices[0])

    def _play_macro_thread(self, selected_macro):
        mouse_controller = mouse.Controller()
        self.running_status.config(text="Status: Running", fg="green")

        while True:
            start_time = time.time()
            for action, action_time in self.macros[selected_macro]:
                if self.use_custom_delays_offsets:
                    if action[0] == 'click':
                        x, y = action[1]
                        x += random.randint(-self.x_offset, self.x_offset)
                        y += random.randint(-self.y_offset, self.y_offset)
                        mouse_controller.position = (x, y)
                        mouse_controller.click(action[2])
                        time.sleep(random.uniform(self.delay_min, self.delay_max))
                else:
                    elapsed = action_time - self.start_time
                    time.sleep(elapsed - (time.time() - start_time))
                    if action[0] == 'click':
                        mouse_controller.position = action[1]
                        mouse_controller.click(action[2])

            if not self.loop:
                break

        self.running_status.config(text="Status: Not running", fg="red")
        print(f"Macro '{selected_macro}' played.")

    def delete_macro(self):
        selected_indices = self.macro_list.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "No macro selected.")
            return None

        selected_macro = self.macro_list.get(selected_indices[0])
        del self.macros[selected_macro]
        self.save_macros()
        self.update_macro_list()

    def toggle_loop(self):
        self.loop = not self.loop
        if self.loop:
            self.loop_status.config(text="Looping: ON", fg="green")
        else:
            self.loop_status.config(text="Looping: OFF", fg="red")

    def open_settings(self):
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Settings")

        ttk.Label(settings_dialog, text="Minimum Delay (seconds):").grid(column=0, row=0, padx=5, pady=5)
        min_delay_entry = ttk.Entry(settings_dialog)
        min_delay_entry.insert(0, str(self.delay_min))
        min_delay_entry.grid(column=1, row=0, padx=5, pady=5)

        ttk.Label(settings_dialog, text="Maximum Delay (seconds):").grid(column=0, row=1, padx=5, pady=5)
        max_delay_entry = ttk.Entry(settings_dialog)
        max_delay_entry.insert(0, str(self.delay_max))
        max_delay_entry.grid(column=1, row=1, padx=5, pady=5)

        ttk.Label(settings_dialog, text="X Offset (pixels):").grid(column=0, row=2, padx=5, pady=5)
        x_offset_entry = ttk.Entry(settings_dialog)
        x_offset_entry.insert(0, str(self.x_offset))
        x_offset_entry.grid(column=1, row=2, padx=5, pady=5)

        ttk.Label(settings_dialog, text="Y Offset (pixels):").grid(column=0, row=3, padx=5, pady=5)
        y_offset_entry = ttk.Entry(settings_dialog)
        y_offset_entry.insert(0, str(self.y_offset))
        y_offset_entry.grid(column=1, row=3, padx=5, pady=5)

        use_custom_delays_offsets_var = tk.BooleanVar(value=self.use_custom_delays_offsets)
        custom_delays_offsets_checkbox = ttk.Checkbutton(
            settings_dialog,
            text="Use Custom Delays and Offsets",
            variable=use_custom_delays_offsets_var
        )
        custom_delays_offsets_checkbox.grid(column=0, row=4, columnspan=2, padx=5, pady=5)

        def save_settings():
            self.delay_min = float(min_delay_entry.get())
            self.delay_max = float(max_delay_entry.get())
            self.x_offset = int(x_offset_entry.get())
            self.y_offset = int(y_offset_entry.get())
            self.use_custom_delays_offsets = use_custom_delays_offsets_var.get()
            settings_dialog.destroy()

        save_button = ttk.Button(settings_dialog, text="Save", command=save_settings)
        save_button.grid(column=0, row=5, columnspan=2, padx=5, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroMaker(root)
    root.mainloop()
