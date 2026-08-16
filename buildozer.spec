[app]
title = Telegram Zip Splitter
package.name = telepacker
package.domain = com.sultanpur
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.1
requirements = python3,kivy,plyer
orientation = portrait
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = armeabi-v7a, arm64-v8a
android.allow_backup = True
# Required for Android 10 (including Redmi 9) to retain shared-storage access.
# Android 11+ is handled by the in-app "All files access" settings flow.
android.extra_manifest_application_arguments = android_manifest_application_args.xml
android.numeric_version = 2

[buildozer]
log_level = 2
warn_on_root = 0
