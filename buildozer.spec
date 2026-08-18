[app]

title = Telegram Zip Splitter

package.name = zippacker

package.domain = org.test

source.dir = .

source.include_exts = py,png,jpg,kv,atlas

version = 1.0.1

requirements = python3,kivy,plyer

orientation = portrait

fullscreen = 0


# Android permissions
#
# READ/WRITE are kept for compatibility with older Android.
# MANAGE_EXTERNAL_STORAGE is included because the Python
# filesystem needs broad access on newer Android versions.

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE


# Android versions

android.api = 33

android.minapi = 21


# Build for both common ARM Android architectures.

android.archs = arm64-v8a,armeabi-v7a


# Android application settings

android.allow_backup = True

android.accept_sdk_license = True


# Keep the application simple.

android.presplash_color = #FFFFFF


[buildozer]

log_level = 2

warn_on_root = 0
# In buildozer.spec
requirements = python3,kivy,plyer
# Add pip version constraint
p4a.pip_version = 23.1.2
