import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

import 'api_service.dart';
import 'app_store.dart';
import 'superadmin_api_service.dart';

/// AppStore extension that keeps an explicit server logout intact while still
/// allowing a later biometric re-login.
///
/// The server session token is deliberately deleted by [AppStore.logout]. When
/// biometrics are enabled, the last successfully verified username/password are
/// therefore kept separately in Android/iOS secure storage. They are only read
/// after successful device authentication and are removed immediately when the
/// user disables biometric login.
class BiometricAppStore extends AppStore {
  BiometricAppStore({ApiService? api, super.initialize = true})
      : super(api: api ?? SuperAdminApiService());

  static const _usernameKey = 'flapamamaku_biometric_username';
  static const _passwordKey = 'flapamamaku_biometric_password';

  final FlutterSecureStorage _biometricStorage = const FlutterSecureStorage();
  final LocalAuthentication _biometricAuth = LocalAuthentication();

  Future<void> _saveBiometricCredentials(
    String username,
    String password,
  ) async {
    if (!biometricEnabled || username.trim().isEmpty || password.isEmpty) return;
    await _biometricStorage.write(
      key: _usernameKey,
      value: username.trim(),
    );
    await _biometricStorage.write(
      key: _passwordKey,
      value: password,
    );
  }

  Future<void> _clearBiometricCredentials() async {
    await _biometricStorage.delete(key: _usernameKey);
    await _biometricStorage.delete(key: _passwordKey);
  }

  @override
  Future<bool> login(String username, String password) async {
    final ok = await super.login(username, password);
    if (ok && isAuthenticated && !mustChangePassword) {
      await _saveBiometricCredentials(username, password);
    }
    return ok;
  }

  @override
  Future<bool> loginWithBiometrics() async {
    if (isBiometricAuthenticating) return false;
    if (!biometricEnabled) {
      authError = 'Biometrische Anmeldung ist in den Einstellungen nicht aktiviert.';
      notifyListeners();
      return false;
    }

    try {
      biometricAvailable = await _biometricAuth.isDeviceSupported();
      if (!biometricAvailable) {
        biometricAvailable = await _biometricAuth.canCheckBiometrics;
      }
    } catch (_) {
      biometricAvailable = false;
    }

    if (!biometricAvailable) {
      authError = 'Auf diesem Gerät ist keine biometrische Anmeldung verfügbar.';
      notifyListeners();
      return false;
    }

    final username = await _biometricStorage.read(key: _usernameKey);
    final password = await _biometricStorage.read(key: _passwordKey);
    if (username == null ||
        username.trim().isEmpty ||
        password == null ||
        password.isEmpty) {
      authError =
          'Bitte nach diesem Update einmal mit Benutzername und Passwort anmelden. Danach funktioniert die biometrische Anmeldung auch nach dem Abmelden.';
      notifyListeners();
      return false;
    }

    isBiometricAuthenticating = true;
    authError = null;
    notifyListeners();

    try {
      final authenticated = await _biometricAuth.authenticate(
        localizedReason: '$appName anmelden',
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
      if (!authenticated) return false;

      return await super.login(username, password);
    } catch (_) {
      authError = 'Biometrische Anmeldung konnte nicht verwendet werden.';
      notifyListeners();
      return false;
    } finally {
      isBiometricAuthenticating = false;
      notifyListeners();
    }
  }

  @override
  Future<bool> setBiometricEnabled(bool enabled) async {
    final ok = await super.setBiometricEnabled(enabled);
    if (ok && !enabled) {
      await _clearBiometricCredentials();
    }
    return ok;
  }

  @override
  Future<bool> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    final ok = await super.changePassword(currentPassword, newPassword);
    if (ok && biometricEnabled) {
      final username = await _biometricStorage.read(key: _usernameKey);
      if (username != null && username.trim().isNotEmpty) {
        await _biometricStorage.write(
          key: _passwordKey,
          value: newPassword,
        );
      }
    }
    return ok;
  }
}
