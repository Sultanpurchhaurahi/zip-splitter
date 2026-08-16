import os
import zipfile
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from plyer import filechooser

class ZipPackerApp(App):
    def build(self):
        self.source_folder = ""
        self.output_folder = ""

        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        layout.add_widget(Label(text="Telegram Zip Splitter", font_size='20sp', size_hint_y=None, height=40))

        self.btn_src = Button(text="Select Source Folder", size_hint_y=None, height=50)
        self.btn_src.bind(on_press=self.choose_source)
        layout.add_widget(self.btn_src)

        self.lbl_src = Label(text="Source: Not selected", size_hint_y=None, height=30)
        layout.add_widget(self.lbl_src)

        self.btn_out = Button(text="Select Output Folder", size_hint_y=None, height=50)
        self.btn_out.bind(on_press=self.choose_output)
        layout.add_widget(self.btn_out)

        self.lbl_out = Label(text="Output: Not selected", size_hint_y=None, height=30)
        layout.add_widget(self.lbl_out)

        self.txt_size = TextInput(text="1.95", multiline=False, size_hint_y=None, height=40, hint_text="Max GB per zip")
        layout.add_widget(self.txt_size)

        self.btn_start = Button(text="Start Packing", size_hint_y=None, height=55, background_color=(0.2, 0.7, 0.3, 1))
        self.btn_start.bind(on_press=self.start_packing)
        layout.add_widget(self.btn_start)

        self.scroll = ScrollView()
        self.lbl_log = Label(text="", size_hint_y=None)
        self.lbl_log.bind(texture_size=self.lbl_log.setter('size'))
        self.scroll.add_widget(self.lbl_log)
        layout.add_widget(self.scroll)

        return layout

    def choose_source(self, instance):
        filechooser.choose_dir(on_selection=self.on_src_select)

    def on_src_select(self, selection):
        if selection:
            self.source_folder = selection[0]
            self.lbl_src.text = f"Source: {self.source_folder}"

    def choose_output(self, instance):
        filechooser.choose_dir(on_selection=self.on_out_select)

    def on_out_select(self, selection):
        if selection:
            self.output_folder = selection[0]
            self.lbl_out.text = f"Output: {self.output_folder}"

    def log(self, text):
        self.lbl_log.text += text + "\n"

    def start_packing(self, instance):
        if not self.source_folder or not self.output_folder:
            self.log("Please choose both source and output folders first.")
            return

        try:
            max_gb = float(self.txt_size.text)
        except ValueError:
            max_gb = 1.95

        MAX_BYTES = int(max_gb * 1024 * 1024 * 1024)
        all_files, skipped = [], []

        for root, _, filenames in os.walk(self.source_folder):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if not os.path.islink(filepath):
                    sz = os.path.getsize(filepath)
                    if sz > MAX_BYTES:
                        skipped.append((filepath, sz))
                    else:
                        all_files.append((filepath, sz))

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

        self.log(f"Creating {len(bins)} zip archives...")

        for index, b in enumerate(bins, 1):
            zip_name = f"{len(b['files'])}_files_part{index}.zip"
            zip_path = os.path.join(self.output_folder, zip_name)
            self.log(f"Writing {zip_name}...")
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for filepath in b['files']:
                    rel_path = os.path.relpath(filepath, self.source_folder)
                    zf.write(filepath, arcname=rel_path)

        self.log("All archives completed!")

if __name__ == '__main__':
    ZipPackerApp().run()
