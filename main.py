import os
import zipfile
import threading
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.utils import platform

class FolderPickerPopup(Popup):
    def __init__(self, default_path, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Folder (Browse & click Select)"
        self.size_hint = (0.95, 0.9)
        self.callback = callback

        if not os.path.exists(default_path):
            default_path = "/storage/emulated/0" if os.path.exists("/storage/emulated/0") else "/"

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.filechooser = FileChooserListView(
            path=default_path,
            dirselect=True,
            filters=['!*']
        )
        layout.add_widget(self.filechooser)

        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)

        btn_cancel = Button(text="Cancel")
        btn_cancel.bind(on_press=self.dismiss)
        btn_layout.add_widget(btn_cancel)

        btn_select = Button(text="Select This Folder", background_color=(0.2, 0.7, 0.3, 1))
        btn_select.bind(on_press=self.select_folder)
        btn_layout.add_widget(btn_select)

        layout.add_widget(btn_layout)
        self.content = layout

    def select_folder(self, instance):
        chosen = self.filechooser.selection[0] if self.filechooser.selection else self.filechooser.path
        self.callback(chosen)
        self.dismiss()

class ZipPackerApp(App):
    def build(self):
        default_dir = "/storage/emulated/0" if os.path.exists("/storage/emulated/0") else os.path.expanduser("~")

        root = BoxLayout(orientation='vertical', padding=15, spacing=10)

        root.add_widget(Label(text="Telegram Zip Splitter", font_size='22sp', bold=True, size_hint_y=None, height=40))

        # Source Folder Input + Browse Button
        root.add_widget(Label(text="Source Folder (Folder to pack):", size_hint_y=None, height=25))
        src_box = BoxLayout(size_hint_y=None, height=45, spacing=5)
        self.txt_src = TextInput(text=default_dir, multiline=False)
        src_box.add_widget(self.txt_src)
        btn_browse_src = Button(text="Browse", size_hint_x=0.3)
        btn_browse_src.bind(on_press=lambda x: self.open_picker(self.txt_src))
        src_box.add_widget(btn_browse_src)
        root.add_widget(src_box)

        # Output Folder Input + Browse Button
        root.add_widget(Label(text="Output Folder (Where to save zips):", size_hint_y=None, height=25))
        out_box = BoxLayout(size_hint_y=None, height=45, spacing=5)
        self.txt_out = TextInput(text=os.path.join(default_dir, "Download", "TelegramZips"), multiline=False)
        out_box.add_widget(self.txt_out)
        btn_browse_out = Button(text="Browse", size_hint_x=0.3)
        btn_browse_out.bind(on_press=lambda x: self.open_picker(self.txt_out))
        out_box.add_widget(btn_browse_out)
        root.add_widget(out_box)

        # Max Size Input
        size_box = BoxLayout(size_hint_y=None, height=45, spacing=10)
        size_box.add_widget(Label(text="Max Zip Size (GB):", size_hint_x=0.5))
        self.txt_size = TextInput(text="1.95", multiline=False, size_hint_x=0.5)
        size_box.add_widget(self.txt_size)
        root.add_widget(size_box)

        # Start Button
        self.btn_start = Button(text="Start Packing", size_hint_y=None, height=55, background_color=(0.2, 0.7, 0.3, 1), bold=True)
        self.btn_start.bind(on_press=self.start_packing_thread)
        root.add_widget(self.btn_start)

        # Log Output Window
        scroll = ScrollView()
        self.lbl_log = Label(text="Ready to pack.\n", size_hint_y=None, halign='left', valign='top')
        self.lbl_log.bind(texture_size=lambda instance, value: setattr(instance, 'height', value))
        self.lbl_log.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        scroll.add_widget(self.lbl_log)
        root.add_widget(scroll)

        return root

    def on_start(self):
        # Request standard permissions safely after UI is rendered
        if platform == 'android':
            Clock.schedule_once(self.request_android_permissions, 0.5)

    def request_android_permissions(self, dt):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            self.log(f"Permission init note: {e}")

    def open_picker(self, target_input):
        current_path = target_input.text if os.path.exists(target_input.text) else "/storage/emulated/0"
        popup = FolderPickerPopup(default_path=current_path, callback=lambda path: setattr(target_input, 'text', path))
        popup.open()

    @mainthread
    def log(self, text):
        self.lbl_log.text += text + "\n"

    @mainthread
    def set_start_button_state(self, enabled, text="Start Packing"):
        self.btn_start.disabled = not enabled
        self.btn_start.text = text

    def start_packing_thread(self, instance):
        self.set_start_button_state(False, "Packing in progress...")
        thread = threading.Thread(target=self.run_packer_task)
        thread.daemon = True
        thread.start()

    def run_packer_task(self):
        try:
            source_folder = self.txt_src.text.strip()
            output_folder = self.txt_out.text.strip()

            if not os.path.exists(source_folder):
                self.log(f"❌ Error: Source folder does not exist:\n{source_folder}")
                self.set_start_button_state(True)
                return

            try:
                max_gb = float(self.txt_size.text)
            except ValueError:
                max_gb = 1.95

            MAX_BYTES = int(max_gb * 1024 * 1024 * 1024)
            os.makedirs(output_folder, exist_ok=True)

            self.log(f"Scanning: {source_folder} ...")
            all_files, skipped = [], []

            for root, _, filenames in os.walk(source_folder):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    if not os.path.islink(filepath):
                        try:
                            sz = os.path.getsize(filepath)
                            if sz > MAX_BYTES:
                                skipped.append((filepath, sz))
                            else:
                                all_files.append((filepath, sz))
                        except Exception as e:
                            self.log(f"Warning: Could not read {filename}: {e}")

            if not all_files:
                self.log("No files found in source folder.")
                self.set_start_button_state(True)
                return

            all_files.sort(key=lambda x: x, reverse=True)

            bins = []
            for filepath, size in all_files:
                placed = False
                for b in bins:
                    if b['current_size'] + size <= MAX_BYTES:
                        b['files'].append(filepath)
                        b['current_size'] += size
                        placed = True
                        break
                if not placed:
                    bins.append({'current_size': size, 'files': [filepath]})

            self.log(f"Packing {len(all_files)} files into {len(bins)} zip archives...")

            for index, b in enumerate(bins, 1):
                zip_name = f"{len(b['files'])}_files_part{index}.zip"
                zip_path = os.path.join(output_folder, zip_name)
                self.log(f"Writing {zip_name} ({b['current_size'] / (1024**3):.2f} GB)...")
                try:
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        for filepath in b['files']:
                            rel_path = os.path.relpath(filepath, source_folder)
                            zf.write(filepath, arcname=rel_path)
                except Exception as e:
                    self.log(f"Error creating {zip_name}: {e}")

            if skipped:
                self.log(f"⚠️ Skipped {len(skipped)} files (exceeded {max_gb} GB each).")

            self.log("✅ All eligible files successfully packed!")
        except Exception as e:
            self.log(f"❌ Error occurred: {e}")
        finally:
            self.set_start_button_state(True, "Start Packing")

if __name__ == '__main__':
    ZipPackerApp().run()
