import os
import threading
import zipfile

from kivy.app import App
from kivy.clock import Clock
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

        layout = BoxLayout(
            orientation="vertical",
            padding=15,
            spacing=10
        )

        title = Label(
            text="Telegram Zip Splitter",
            font_size="20sp",
            size_hint_y=None,
            height=45
        )
        layout.add_widget(title)

        self.btn_src = Button(
            text="Select Source Folder",
            size_hint_y=None,
            height=55
        )
        self.btn_src.bind(on_press=self.choose_source)
        layout.add_widget(self.btn_src)

        self.lbl_src = Label(
            text="Source: Not selected",
            size_hint_y=None,
            height=45,
            shorten=True,
            shorten_from="right"
        )
        layout.add_widget(self.lbl_src)

        self.btn_out = Button(
            text="Select Output Folder",
            size_hint_y=None,
            height=55
        )
        self.btn_out.bind(on_press=self.choose_output)
        layout.add_widget(self.btn_out)

        self.lbl_out = Label(
            text="Output: Not selected",
            size_hint_y=None,
            height=45,
            shorten=True,
            shorten_from="right"
        )
        layout.add_widget(self.lbl_out)

        self.txt_size = TextInput(
            text="1.95",
            multiline=False,
            input_filter="float",
            size_hint_y=None,
            height=50,
            hint_text="Maximum GB per ZIP"
        )
        layout.add_widget(self.txt_size)

        self.btn_start = Button(
            text="Start Packing",
            size_hint_y=None,
            height=60
        )
        self.btn_start.bind(on_press=self.start_packing)
        layout.add_widget(self.btn_start)

        scroll = ScrollView()

        self.lbl_log = Label(
            text="",
            size_hint_y=None,
            halign="left",
            valign="top"
        )

        self.lbl_log.bind(
            texture_size=self.lbl_log.setter("size")
        )

        scroll.add_widget(self.lbl_log)
        layout.add_widget(scroll)

        return layout

    # ----------------------------
    # Folder selection
    # ----------------------------

    def choose_source(self, instance):
        try:
            filechooser.choose_dir(
                on_selection=self.on_src_select
            )
        except Exception as e:
            self.log("Folder picker error: " + str(e))

    def on_src_select(self, selection):
        if selection:
            self.source_folder = selection[0]
            self.lbl_src.text = (
                "Source: " + self.source_folder
            )
            self.log("Source folder selected.")

    def choose_output(self, instance):
        try:
            filechooser.choose_dir(
                on_selection=self.on_out_select
            )
        except Exception as e:
            self.log("Folder picker error: " + str(e))

    def on_out_select(self, selection):
        if selection:
            self.output_folder = selection[0]
            self.lbl_out.text = (
                "Output: " + self.output_folder
            )
            self.log("Output folder selected.")

    # ----------------------------
    # Logging
    # ----------------------------

    def log(self, text):
        Clock.schedule_once(
            lambda dt: self._add_log(text)
        )

    def _add_log(self, text):
        self.lbl_log.text += text + "\n"

    # ----------------------------
    # Start
    # ----------------------------

    def start_packing(self, instance):

        if not self.source_folder:
            self.log("Please select a source folder.")
            return

        if not self.output_folder:
            self.log("Please select an output folder.")
            return

        try:
            max_gb = float(self.txt_size.text)

            if max_gb <= 0:
                raise ValueError

        except Exception:
            max_gb = 1.95
            self.txt_size.text = "1.95"

        max_bytes = int(
            max_gb * 1024 * 1024 * 1024
        )

        self.btn_start.disabled = True

        self.log("")
        self.log("Starting...")
        self.log(
            "Maximum ZIP size: %.2f GB" % max_gb
        )

        # Run ZIP work away from the UI thread.
        thread = threading.Thread(
            target=self.pack_files,
            args=(max_bytes,),
            daemon=True
        )

        thread.start()

    # ----------------------------
    # ZIP creation
    # ----------------------------

    def pack_files(self, max_bytes):

        try:

            all_files = []
            skipped = []

            self.log("Scanning files...")

            for root, dirs, filenames in os.walk(
                self.source_folder
            ):

                for filename in filenames:

                    filepath = os.path.join(
                        root,
                        filename
                    )

                    try:

                        if os.path.islink(filepath):
                            continue

                        size = os.path.getsize(filepath)

                        if size > max_bytes:
                            skipped.append(
                                (filepath, size)
                            )
                        else:
                            all_files.append(
                                (filepath, size)
                            )

                    except Exception as e:
                        self.log(
                            "Cannot read: " + filepath
                        )
                        self.log(
                            "Reason: " + str(e)
                        )

            self.log(
                "Files found: %d" %
                len(all_files)
            )

            self.log(
                "Files too large: %d" %
                len(skipped)
            )

            if not all_files:

                self.log(
                    "No usable files were found."
                )

                Clock.schedule_once(
                    lambda dt: self.finish()
                )

                return

            # IMPORTANT:
            # Sort by SIZE, largest first.
            all_files.sort(
                key=lambda item: item[1],
                reverse=True
            )

            # First-fit decreasing bins.
            bins = []

            for filepath, size in all_files:

                placed = False

                for current_bin in bins:

                    if (
                        current_bin["current_size"]
                        + size
                        <= max_bytes
                    ):

                        current_bin["files"].append(
                            (filepath, size)
                        )

                        current_bin["current_size"] += size

                        placed = True
                        break

                if not placed:

                    bins.append(
                        {
                            "current_size": size,
                            "files": [
                                (filepath, size)
                            ]
                        }
                    )

            self.log(
                "Creating %d ZIP archive(s)..."
                % len(bins)
            )

            # ------------------------
            # Create ZIP files
            # ------------------------

            for index, current_bin in enumerate(
                bins,
                start=1
            ):

                zip_name = (
                    "part%d.zip" % index
                )

                zip_path = os.path.join(
                    self.output_folder,
                    zip_name
                )

                self.log(
                    "Writing %s..." % zip_name
                )

                try:

                    with zipfile.ZipFile(
                        zip_path,
                        "w",
                        compression=zipfile.ZIP_DEFLATED,
                        compresslevel=6
                    ) as zf:

                        for filepath, size in (
                            current_bin["files"]
                        ):

                            relative_path = os.path.relpath(
                                filepath,
                                self.source_folder
                            )

                            try:

                                zf.write(
                                    filepath,
                                    arcname=relative_path
                                )

                            except Exception as e:

                                self.log(
                                    "Failed: "
                                    + relative_path
                                )

                                self.log(
                                    "Reason: "
                                    + str(e)
                                )

                except Exception as e:

                    self.log(
                        "ERROR creating "
                        + zip_name
                    )

                    self.log(
                        str(e)
                    )

                    continue

                self.log(
                    "Finished %s" % zip_name
                )

            # ------------------------
            # Skipped files
            # ------------------------

            if skipped:

                self.log("")
                self.log(
                    "Skipped files larger than "
                    "the selected limit:"
                )

                for filepath, size in skipped:

                    self.log(
                        os.path.basename(filepath)
                        + " (%.2f GB)" %
                        (
                            size /
                            (1024 ** 3)
                        )
                    )

            self.log("")
            self.log("All archives completed!")

        except Exception as e:

            self.log("")
            self.log("ERROR:")
            self.log(str(e))

        finally:

            Clock.schedule_once(
                lambda dt: self.finish()
            )

    # ----------------------------
    # Re-enable button
    # ----------------------------

    def finish(self):

        self.btn_start.disabled = False


if __name__ == "__main__":
    ZipPackerApp().run()
