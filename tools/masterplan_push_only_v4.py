from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"marker not found: {label}")
    return text.replace(old, new, 1)

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
text = replace_once(text, old_init, new_init, 'firebase default app guard')
push.write_text(text)

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
text = replace_once(text, old, new, 'persistent push diagnostic')
settings.write_text(text)
print('source-only push v4 patch applied')
