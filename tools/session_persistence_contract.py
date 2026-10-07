"""Guard the intended mobile session semantics.

A valid stored token must be restored on startup even when biometric login is
enabled. Only an explicit logout (or genuine token invalidation) may end the
session; biometric support remains an optional login helper.
"""

from pathlib import Path

source = Path("lib/data/app_store.dart").read_text(encoding="utf-8")

start = source.index("Future<void> restoreSession() async")
end = source.index("Future<void> _restoreWithToken", start)
restore = source[start:end]

assert "final token = await _secureStorage.read(key: 'flapamamaku_token');" in restore
assert "await _restoreWithToken(token);" in restore
assert "if (biometricEnabled && biometricAvailable)" not in restore
assert "biometricUnlockPending = true;" not in restore

logout_start = source.index("Future<void> logout() async")
logout_tail = source[logout_start:logout_start + 1800]
assert "await _secureStorage.delete(key: 'flapamamaku_token');" in logout_tail

assert "Future<bool> loginWithBiometrics() async" in source
assert "Future<bool> setBiometricEnabled(bool enabled) async" in source

print("SESSION PERSISTENCE CONTRACT OK")
