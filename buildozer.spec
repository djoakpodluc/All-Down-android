[app]

title = AllDown
package.name = alldown
package.domain = org.alldown

source.dir = .
source.include_exts = py,png,jpg,kv,json

version = 1.0

# Dépendances : on reste volontairement minimal pour maximiser les chances
# de compilation réussie. yt-dlp fonctionne même sans pycryptodomex/brotli
# (il s'en passe simplement pour certains sites très spécifiques).
requirements = python3,kivy==2.3.1,yt-dlp,plyer,certifi,pyjnius

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS,FOREGROUND_SERVICE,ACCESS_NETWORK_STATE

# Reçoit les liens partagés depuis YouTube/TikTok/Instagram (bouton "Partager")
android.manifest.intent_filters = android_intent_filters.xml

android.api = 33
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
