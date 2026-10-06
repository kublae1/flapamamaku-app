from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"marker not found: {label}")
    return text.replace(old, new, 1)

# 1) Build workflow: native Firebase resources, monotonic date-based versionCode,
# unique APK/artifact names and signature verification.
workflow = Path('.github/workflows/recovery-build-android.yml')
text = workflow.read_text()

marker = "      - name: Configure Android permissions, push icon and biometric activity\n"
native_firebase = r'''      - name: Configure native Firebase Android resources
        shell: bash
        run: |
          mkdir -p android/app/src/main/res/values
          cat > android/app/src/main/res/values/firebase_generated.xml <<EOF
          <?xml version="1.0" encoding="utf-8"?>
          <resources>
              <string name="google_app_id" translatable="false">$FIREBASE_APP_ID_VALUE</string>
              <string name="gcm_defaultSenderId" translatable="false">$FIREBASE_MESSAGING_SENDER_ID_VALUE</string>
              <string name="project_id" translatable="false">$FIREBASE_PROJECT_ID_VALUE</string>
              <string name="google_api_key" translatable="false">$FIREBASE_API_KEY_VALUE</string>
          </resources>
          EOF
          test -s android/app/src/main/res/values/firebase_generated.xml

'''
if native_firebase not in text:
    if marker not in text:
        raise SystemExit('workflow firebase insertion marker not found')
    text = text.replace(marker, native_firebase + marker, 1)

text = replace_once(
    text,
    '          APP_BUILD_NUMBER=$((GITHUB_RUN_NUMBER + 1000))\n          echo "name=$APP_VERSION" >> "$GITHUB_OUTPUT"\n          echo "number=$APP_BUILD_NUMBER" >> "$GITHUB_OUTPUT"\n          echo "Release version: $APP_VERSION+$APP_BUILD_NUMBER"\n',
    '''          APP_BUILD_NUMBER=$(python3 - <<'PY'\nimport os\nfrom datetime import datetime, timezone\ndate_code = int(datetime.now(timezone.utc).strftime('%y%m%d'))\nrun_suffix = int(os.environ['GITHUB_RUN_NUMBER']) % 1000\nprint(date_code * 1000 + run_suffix)\nPY\n          )\n          APK_FILE="flapamamaku-${APP_VERSION}-${APP_BUILD_NUMBER}.apk"\n          echo "name=$APP_VERSION" >> "$GITHUB_OUTPUT"\n          echo "number=$APP_BUILD_NUMBER" >> "$GITHUB_OUTPUT"\n          echo "apk_file=$APK_FILE" >> "$GITHUB_OUTPUT"\n          echo "Release version: $APP_VERSION+$APP_BUILD_NUMBER ($APK_FILE)"\n''',
    'date based version code',
)

old_tail = '''      - name: Checksum
        run: sha256sum build/app/outputs/flutter-apk/app-release.apk > build/app/outputs/flutter-apk/SHA256SUMS.txt
      - uses: actions/upload-artifact@v4
        with:
          name: flapamamaku-masterplan-recovered-test
          path: |
            build/app/outputs/flutter-apk/app-release.apk
            build/app/outputs/flutter-apk/SHA256SUMS.txt
'''
new_tail = '''      - name: Verify signature and prepare uniquely named APK
        env:
          APK_FILE: ${{ steps.version.outputs.apk_file }}
        run: |
          cp build/app/outputs/flutter-apk/app-release.apk "build/app/outputs/flutter-apk/$APK_FILE"
          APKSIGNER=$(find "$ANDROID_HOME/build-tools" -type f -name apksigner | sort -V | tail -n 1)
          if [ -z "$APKSIGNER" ]; then
            echo "::error::apksigner not found"
            exit 1
          fi
          "$APKSIGNER" verify --print-certs "build/app/outputs/flutter-apk/$APK_FILE"
          sha256sum "build/app/outputs/flutter-apk/$APK_FILE" > build/app/outputs/flutter-apk/SHA256SUMS.txt
      - uses: actions/upload-artifact@v4
        with:
          name: flapamamaku-${{ steps.version.outputs.name }}-build-${{ steps.version.outputs.number }}
          path: |
            build/app/outputs/flutter-apk/${{ steps.version.outputs.apk_file }}
            build/app/outputs/flutter-apk/SHA256SUMS.txt
'''
text = replace_once(text, old_tail, new_tail, 'unique artifact output')
workflow.write_text(text)

# 2) FCM: allow native FirebaseInitProvider to create the default app first.
push = Path('lib/data/push_service.dart')
text = push.read_text()
old_init = '''        await Firebase.initializeApp(
          options: const FirebaseOptions(
            apiKey: _apiKey,
            appId: _appId,
            messagingSenderId: _senderId,
            projectId: _projectId,
          ),
        );
'''
new_init = '''        if (Firebase.apps.isEmpty) {
          await Firebase.initializeApp(
            options: const FirebaseOptions(
              apiKey: _apiKey,
              appId: _appId,
              messagingSenderId: _senderId,
              projectId: _projectId,
            ),
          );
        }
'''
text = replace_once(text, old_init, new_init, 'firebase native/default init guard')
push.write_text(text)

# 3) Expose persistent push diagnostics to Settings.
store = Path('lib/data/app_store.dart')
text = store.read_text()
marker = '  bool get serverConfigured => api.isConfigured;\n'
if 'String? get pushDiagnostic' not in text:
    text = replace_once(
        text,
        marker,
        marker + '  String? get pushDiagnostic => pushService.lastError;\n',
        'push diagnostic getter',
    )
store.write_text(text)

settings = Path('lib/screens/settings_screen.dart')
text = settings.read_text()
old = '''              subtitle: Text(
                store.pushEnabled
                    ? 'Push ist auf diesem Gerät aktiviert'
                    : 'Beim Einschalten werden Firebase, Android-Berechtigung und Serverregistrierung geprüft',
                style: const TextStyle(color: Colors.white60),
              ),
'''
new = '''              subtitle: Text(
                store.pushEnabled
                    ? 'Push ist auf diesem Gerät aktiviert'
                    : (store.pushDiagnostic?.isNotEmpty == true
                        ? store.pushDiagnostic!
                        : 'Beim Einschalten werden Firebase, Android-Berechtigung, FCM-Token und Serverregistrierung geprüft'),
                style: TextStyle(
                  color: store.pushDiagnostic?.isNotEmpty == true
                      ? Colors.orangeAccent
                      : Colors.white60,
                ),
              ),
'''
text = replace_once(text, old, new, 'persistent push diagnostic UI')
settings.write_text(text)

print('masterplan push/build v3 patch applied')
