import os
import threading
import time
import zipfile

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform


class FolderPickerPopup(Popup):
    def __init__(self, default_path, callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Folder"
        self.size_hint = (0.95, 0.9)
        self.callback = callback

        if not os.path.isdir(default_path):
            default_path = "/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else "/"

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        self.filechooser = FileChooserListView(
            path=default_path,
            dirselect=True,
            filters=["!*"],
        )
        layout.add_widget(self.filechooser)

        buttons = BoxLayout(size_hint_y=None, height=50, spacing=10)
        cancel = Button(text="Cancel")
        cancel.bind(on_press=self.dismiss)
        buttons.add_widget(cancel)

        select = Button(text="Select This Folder", background_color=(0.2, 0.7, 0.3, 1))
        select.bind(on_press=self.select_folder)
        buttons.add_widget(select)
        layout.add_widget(buttons)
        self.content = layout

    def select_folder(self, _instance):
        chosen = self.filechooser.selection[0] if self.filechooser.selection else self.filechooser.path
        self.callback(chosen)
        self.dismiss()


class ZipPackerApp(App):
    def build(self):
        default_dir = self.shared_storage_root()

        root = BoxLayout(orientation="vertical", padding=15, spacing=10)
        root.add_widget(Label(text="Telegram Zip Splitter", font_size="22sp", bold=True,
                              size_hint_y=None, height=40))

        self.lbl_permission = Label(text="Checking storage access...", size_hint_y=None, height=36)
        root.add_widget(self.lbl_permission)

        self.btn_permissions = Button(
            text="Grant storage access",
            size_hint_y=None,
            height=45,
            background_color=(0.25, 0.5, 0.85, 1),
        )
        self.btn_permissions.bind(on_press=self.grant_storage_access)
        root.add_widget(self.btn_permissions)

        root.add_widget(Label(text="Source Folder (Folder to pack):", size_hint_y=None, height=25))
        src_box = BoxLayout(size_hint_y=None, height=45, spacing=5)
        self.txt_src = TextInput(text=default_dir, multiline=False)
        src_box.add_widget(self.txt_src)
        browse_src = Button(text="Browse", size_hint_x=0.3)
        browse_src.bind(on_press=lambda _button: self.open_picker(self.txt_src))
        src_box.add_widget(browse_src)
        root.add_widget(src_box)

        root.add_widget(Label(text="Output Folder (Where to save zips):", size_hint_y=None, height=25))
        out_box = BoxLayout(size_hint_y=None, height=45, spacing=5)
        self.txt_out = TextInput(
            text=os.path.join(default_dir, "Download", "TelegramZips"), multiline=False
        )
        out_box.add_widget(self.txt_out)
        browse_out = Button(text="Browse", size_hint_x=0.3)
        browse_out.bind(on_press=lambda _button: self.open_picker(self.txt_out))
        out_box.add_widget(browse_out)
        root.add_widget(out_box)

        size_box = BoxLayout(size_hint_y=None, height=45, spacing=10)
        size_box.add_widget(Label(text="Max Zip Size (GB):", size_hint_x=0.5))
        self.txt_size = TextInput(text="1.95", multiline=False, size_hint_x=0.5)
        size_box.add_widget(self.txt_size)
        root.add_widget(size_box)

        self.btn_start = Button(
            text="Start Packing",
            size_hint_y=None,
            height=55,
            background_color=(0.2, 0.7, 0.3, 1),
            bold=True,
        )
        self.btn_start.bind(on_press=self.start_packing_thread)
        root.add_widget(self.btn_start)

        scroll = ScrollView()
        self.lbl_log = Label(text="Ready to pack.\n", size_hint_y=None, halign="left", valign="top")
        self.lbl_log.bind(texture_size=lambda instance, value: setattr(instance, "height", value))
        self.lbl_log.bind(width=lambda instance, value: setattr(instance, "text_size", (value, None)))
        scroll.add_widget(self.lbl_log)
        root.add_widget(scroll)
        return root

    def on_start(self):
        # Android 10 and lower use the normal runtime permission prompt.
        # Android 11+ use the system "All files access" settings screen instead.
        if platform == "android":
            Clock.schedule_once(lambda _dt: self.refresh_storage_access(request_legacy=True), 0.5)
        else:
            self.set_storage_ui(True)

    def on_resume(self):
        # The user returns here after granting "All files access" in Android Settings.
        if platform == "android":
            Clock.schedule_once(lambda _dt: self.refresh_storage_access(request_legacy=False), 0)

    @staticmethod
    def shared_storage_root():
        android_root = "/storage/emulated/0"
        return android_root if os.path.isdir(android_root) else os.path.expanduser("~")

    @staticmethod
    def android_sdk_int():
        from jnius import autoclass
        return int(autoclass("android.os.Build$VERSION").SDK_INT)

    def has_storage_access(self):
        if platform != "android":
            return True

        try:
            if self.android_sdk_int() >= 30:
                from jnius import autoclass
                environment = autoclass("android.os.Environment")
                return bool(environment.isExternalStorageManager())

            from android.permissions import Permission, check_permission
            return (
                check_permission(Permission.READ_EXTERNAL_STORAGE)
                and check_permission(Permission.WRITE_EXTERNAL_STORAGE)
            )
        except Exception as error:
            self.log(f"Could not check storage permission: {error}")
            return False

    @mainthread
    def set_storage_ui(self, granted):
        if granted:
            self.lbl_permission.text = "Storage access granted"
            self.btn_permissions.disabled = True
            self.btn_permissions.text = "Storage access granted"
        else:
            self.lbl_permission.text = "Storage access is required to browse, read, and write folders."
            self.btn_permissions.disabled = False
            self.btn_permissions.text = "Grant storage access"

    def refresh_storage_access(self, request_legacy=False):
        granted = self.has_storage_access()
        self.set_storage_ui(granted)
        if granted:
            self.log("Storage access is ready.")
            return True

        if request_legacy and self.android_sdk_int() <= 29:
            self.request_legacy_storage_permissions()
        elif self.android_sdk_int() >= 30:
            self.log("Tap 'Grant storage access', enable 'Allow access to manage all files', then return.")
        return False

    def grant_storage_access(self, _instance):
        if self.has_storage_access():
            self.set_storage_ui(True)
            return

        if self.android_sdk_int() >= 30:
            self.open_all_files_access_settings()
        else:
            self.request_legacy_storage_permissions()

    def request_legacy_storage_permissions(self):
        try:
            from android.permissions import Permission, request_permissions
            request_permissions(
                [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE],
                self.on_legacy_permission_result,
            )
        except Exception as error:
            self.log(f"Could not request storage access: {error}")

    @mainthread
    def on_legacy_permission_result(self, _permissions, grants):
        granted = all(grants)
        self.set_storage_ui(granted)
        if granted:
            self.log("Storage access granted.")
        else:
            self.log("Storage access was denied. Tap 'Grant storage access' and allow Files and media.")

    def open_all_files_access_settings(self):
        try:
            from jnius import autoclass

            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            intent = autoclass("android.content.Intent")(
                autoclass("android.provider.Settings").ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION
            )
            uri = autoclass("android.net.Uri").parse("package:" + activity.getPackageName())
            intent.setData(uri)
            activity.startActivity(intent)
            self.log("Enable 'Allow access to manage all files' for this app, then return here.")
        except Exception as error:
            self.log(f"Could not open Android storage settings: {error}")

    def open_picker(self, target_input):
        if not self.refresh_storage_access(request_legacy=False):
            return
        current_path = target_input.text if os.path.isdir(target_input.text) else self.shared_storage_root()
        FolderPickerPopup(
            default_path=current_path,
            callback=lambda path: setattr(target_input, "text", path),
        ).open()

    @mainthread
    def log(self, text):
        self.lbl_log.text += text + "\n"

    @mainthread
    def set_start_button_state(self, enabled, text="Start Packing"):
        self.btn_start.disabled = not enabled
        self.btn_start.text = text

    def start_packing_thread(self, _instance):
        if not self.refresh_storage_access(request_legacy=False):
            if self.android_sdk_int() >= 30:
                self.open_all_files_access_settings()
            return

        # Read widgets only on the Kivy UI thread, then pass plain values to the worker.
        source_folder = self.txt_src.text.strip()
        output_folder = self.txt_out.text.strip()
        size_text = self.txt_size.text.strip()

        self.set_start_button_state(False, "Packing in progress...")
        thread = threading.Thread(
            target=self.run_packer_task,
            args=(source_folder, output_folder, size_text),
            daemon=True,
        )
        thread.start()

    @staticmethod
    def is_within_folder(path, folder):
        try:
            return os.path.commonpath([os.path.realpath(path), os.path.realpath(folder)]) == os.path.realpath(folder)
        except ValueError:
            return False

    def run_packer_task(self, source_folder, output_folder, size_text):
        try:
            if not os.path.isdir(source_folder):
                self.log(f"Error: Source folder does not exist:\n{source_folder}")
                return

            try:
                max_gb = float(size_text)
                if max_gb <= 0:
                    raise ValueError
            except ValueError:
                self.log("Invalid max size. Using 1.95 GB.")
                max_gb = 1.95

            max_bytes = int(max_gb * 1024 * 1024 * 1024)
            os.makedirs(output_folder, exist_ok=True)

            source_real = os.path.realpath(source_folder)
            output_real = os.path.realpath(output_folder)
            output_is_inside_source = self.is_within_folder(output_real, source_real)
            if output_is_inside_source:
                self.log("Existing output archives will be excluded from the source scan.")

            self.log(f"Scanning: {source_folder} ...")
            all_files, skipped = [], []
            for current_root, dirnames, filenames in os.walk(source_folder):
                if output_is_inside_source:
                    dirnames[:] = [
                        name for name in dirnames
                        if not self.is_within_folder(os.path.join(current_root, name), output_real)
                    ]
                for filename in filenames:
                    filepath = os.path.join(current_root, filename)
                    if not os.path.islink(filepath):
                        try:
                            size = os.path.getsize(filepath)
                            if size > max_bytes:
                                skipped.append((filepath, size))
                            else:
                                all_files.append((filepath, size))
                        except OSError as error:
                            self.log(f"Warning: Could not read {filename}: {error}")

            if not all_files:
                self.log("No eligible files found in source folder.")
                return

            # First-fit decreasing makes the archive size limit much more reliable.
            all_files.sort(key=lambda item: item[1], reverse=True)
            bins = []
            for filepath, size in all_files:
                for archive in bins:
                    if archive["current_size"] + size <= max_bytes:
                        archive["files"].append(filepath)
                        archive["current_size"] += size
                        break
                else:
                    bins.append({"current_size": size, "files": [filepath]})

            self.log(f"Packing {len(all_files)} files into {len(bins)} zip archives...")
            batch_id = time.strftime("telegram_zips_%Y%m%d_%H%M%S")
            created = []
            for index, archive in enumerate(bins, 1):
                zip_name = f"{batch_id}_part{index:02d}_of_{len(bins):02d}.zip"
                zip_path = os.path.join(output_folder, zip_name)
                self.log(f"Writing {zip_name} ({archive['current_size'] / (1024 ** 3):.2f} GB)...")
                try:
                    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
                        for filepath in archive["files"]:
                            zip_file.write(filepath, arcname=os.path.relpath(filepath, source_real))
                    created.append(zip_name)
                except (OSError, zipfile.BadZipFile) as error:
                    self.log(f"Error creating {zip_name}: {error}")

            if skipped:
                self.log(f"Skipped {len(skipped)} files that exceed {max_gb:g} GB each.")
            if created:
                self.log(f"Finished: created {len(created)} archive(s) in {output_folder}.")
            else:
                self.log("No archives were created. Check the messages above and free storage space if needed.")
        except Exception as error:
            self.log(f"Unexpected error: {error}")
        finally:
            self.set_start_button_state(True, "Start Packing")


if __name__ == "__main__":
    ZipPackerApp().run()
