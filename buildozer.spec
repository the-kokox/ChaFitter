[app]
title = ChaFitter
package.name = outfitai
package.domain = org.outfitai

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json

version = 0.1
requirements = python3,kivy

# Permisos necesarios en Android: cámara y lectura de imágenes para Android 13+
android.permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

orientation = portrait
fullscreen = 0

# Configuración de API y arquitectura Android
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
