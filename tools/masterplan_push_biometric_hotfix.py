from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"marker not found: {label}")
    return text.replace(old, new, 1)


store = Path("lib/data/app_store.dart")
text = store.read_text()

old_capability = """    try {
      biometricAvailable =
          await _localAuth.canCheckBiometrics &&
          await _localAuth.isDeviceSupported();
    } catch (_) {
      biometricAvailable = false;
    }
"""
new_capability = """    try {
      biometricAvailable = await _localAuth.isDeviceSupported();
      if (!biometricAvailable) {
        biometricAvailable = await _localAuth.canCheckBiometrics;
      }
    } catch (_) {
      biometricAvailable = false;
    }
"""
count = text.count(old_capability)
if count < 3:
    raise SystemExit(f"Expected at least 3 biometric capability blocks, found {count}")
text = text.replace(old_capability, new_capability)

text = replace_once(
    text,
    """    // A valid secure session token keeps the member signed in until
    // they explicitly log out or an administrator revokes the session.
    biometricUnlockPending = false;
    await _restoreWithToken(token);
""",
    """    // When device authentication is enabled, never restore the secured
    // session before the user has unlocked this app instance.
    if (biometricEnabled && biometricAvailable) {
      biometricUnlockPending = true;
      isAuthenticated = false;
      currentUser = null;
      authReady = true;
      notifyListeners();
      return;
    }

    // Without the optional device lock, a valid secure session token keeps
    // the member signed in until logout or server-side session revocation.
    biometricUnlockPending = false;
    await _restoreWithToken(token);
""",
    "restoreSession biometric gate",
)

text = replace_once(
    text,
    """    final ok = await pushService.enable();
    if (!ok) {
      authError =
          'Push-Benachrichtigungen konnten nicht aktiviert werden. Bitte Berechtigung prüfen.';
      notifyListeners();
      return false;
    }
""",
    """    final ok = await pushService.enable();
    if (!ok) {
      authError = pushService.lastError ??
          'Push-Benachrichtigungen konnten nicht aktiviert werden.';
      notifyListeners();
      return false;
    }
""",
    "push diagnostics",
)
store.write_text(text)

push = Path("lib/data/push_service.dart")
text = push.read_text()
text = replace_once(
    text,
    "  bool _initialized = false;\n  void Function(String route)? onRoute;\n",
    "  bool _initialized = false;\n  String? lastError;\n  void Function(String route)? onRoute;\n",
    "push lastError field",
)
text = replace_once(
    text,
    """  Future<bool> enable() async {
    if (!isConfigured || !api.isConfigured || !api.hasToken) return false;

    try {
""",
    """  Future<bool> enable() async {
    lastError = null;
    if (!isConfigured) {
      lastError = 'Firebase-Konfiguration fehlt in diesem App-Build.';
      return false;
    }
    if (!api.isConfigured) {
      lastError = 'Der Vereinsserver ist nicht konfiguriert.';
      return false;
    }
    if (!api.hasToken) {
      lastError = 'Für Push ist zuerst eine gültige Anmeldung erforderlich.';
      return false;
    }

    try {
""",
    "push enable preconditions",
)
text = replace_once(
    text,
    """      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
""",
    """      final messaging = FirebaseMessaging.instance;
      await messaging.setAutoInitEnabled(true);
      final settings = await messaging.requestPermission(
""",
    "push auto-init",
)
text = replace_once(
    text,
    """      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        return false;
      }

      final token = await messaging.getToken();
      if (token == null || token.isEmpty) return false;
""",
    """      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        lastError = 'Die Android-Berechtigung für Benachrichtigungen wurde abgelehnt.';
        return false;
      }

      final token = await messaging.getToken();
      if (token == null || token.isEmpty) {
        lastError = 'Firebase hat kein Geräte-Token geliefert.';
        return false;
      }
""",
    "push permission/token diagnostics",
)
text = replace_once(
    text,
    """      return true;
    } catch (_) {
      return false;
    }
  }
""",
    """      lastError = null;
      return true;
    } catch (error) {
      lastError = 'Push-Initialisierung fehlgeschlagen: $error';
      return false;
    }
  }
""",
    "push exception diagnostics",
)
push.write_text(text)

settings = Path("lib/screens/settings_screen.dart")
text = settings.read_text()
text = replace_once(
    text,
    """              subtitle: Text(
                store.biometricAvailable
                    ? 'App beim nächsten Start mit Fingerabdruck, Gesichtserkennung oder Geräte-PIN entsperren'
                    : 'Auf diesem Gerät ist keine biometrische Entsperrung verfügbar',
                style: const TextStyle(color: Colors.white60),
              ),
              value: store.biometricEnabled && store.biometricAvailable,
""",
    """              subtitle: Text(
                store.biometricEnabled
                    ? 'Beim nächsten App-Start ist die Geräteauthentifizierung vorgeschaltet'
                    : 'Fingerabdruck, Gesichtserkennung oder Geräte-PIN beim App-Start verwenden',
                style: const TextStyle(color: Colors.white60),
              ),
              value: store.biometricEnabled,
""",
    "biometric settings text",
)
text = replace_once(
    text,
    """              onChanged: store.biometricAvailable
                  ? (value) async {
                      final ok = await store.setBiometricEnabled(value);
                      if (!ok && context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              store.authError ??
                                  'Biometrische Anmeldung konnte nicht geändert werden.',
                            ),
                          ),
                        );
                      }
                    }
                  : null,
""",
    """              onChanged: (value) async {
                final ok = await store.setBiometricEnabled(value);
                if (!ok && context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        store.authError ??
                            'Biometrische Anmeldung konnte nicht geändert werden.',
                      ),
                    ),
                  );
                }
              },
""",
    "biometric settings enablement",
)
text = replace_once(
    text,
    """              subtitle: Text(
                store.pushAvailable
                    ? 'Neue News sowie neue oder geänderte Termine auf dem Handy anzeigen'
                    : 'Push-Dienst wird vorbereitet und nach Firebase-Einrichtung verfügbar',
                style: const TextStyle(color: Colors.white60),
              ),
""",
    """              subtitle: Text(
                store.pushEnabled
                    ? 'Push ist auf diesem Gerät aktiviert'
                    : 'Beim Einschalten werden Firebase, Android-Berechtigung und Serverregistrierung geprüft',
                style: const TextStyle(color: Colors.white60),
              ),
""",
    "push settings text",
)
text = replace_once(
    text,
    """              onChanged: store.pushAvailable
                  ? (value) async {
                      final ok = await store.setPushEnabled(value);
                      if (!ok && context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              store.authError ??
                                  'Push-Benachrichtigungen konnten nicht geändert werden.',
                            ),
                          ),
                        );
                      }
                    }
                  : null,
""",
    """              onChanged: (value) async {
                final ok = await store.setPushEnabled(value);
                if (!ok && context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        store.authError ??
                            'Push-Benachrichtigungen konnten nicht geändert werden.',
                      ),
                    ),
                  );
                }
              },
""",
    "push settings enablement",
)
settings.write_text(text)

print("push/biometric hotfix applied")
