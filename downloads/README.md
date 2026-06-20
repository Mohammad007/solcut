# App downloads

Drop the built Android app here so the website's **Download App** button works.

```
backend/downloads/SlotCut.apk
```

- The website serves it at `GET /download/app` (forces a download as `SlotCut.apk`).
- If the file is missing, the route returns 404 and the website shows a
  "coming soon" state instead of a broken button.
- Override the filename/version via env: `APK_FILENAME=SlotCut.apk`, `APP_VERSION=1.0`.

Build the APK from the Flutter app:

```bash
cd ../../slotcut_app
flutter build apk --release
# output: build/app/outputs/flutter-apk/app-release.apk
# then copy it here as SlotCut.apk
```
