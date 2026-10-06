import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

class BiometricLockScreen extends StatefulWidget {
  final VoidCallback? onUnlocked;

  const BiometricLockScreen({super.key, this.onUnlocked});

  @override
  State<BiometricLockScreen> createState() => _BiometricLockScreenState();
}

class _BiometricLockScreenState extends State<BiometricLockScreen> {
  final LocalAuthentication _localAuth = LocalAuthentication();
  bool _started = false;
  bool _authenticating = false;
  String? _localError;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _authenticate();
    });
  }

  Future<void> _authenticate() async {
    if (_authenticating) return;
    final store = AppStoreScope.of(context);

    setState(() {
      _authenticating = true;
      _localError = null;
    });

    try {
      bool ok;
      if (store.biometricUnlockPending) {
        ok = await store.unlockWithBiometrics();
      } else {
        ok = await _localAuth.authenticate(
          localizedReason: '${store.appName} entsperren',
          options: const AuthenticationOptions(
            biometricOnly: false,
            stickyAuth: true,
            useErrorDialogs: true,
          ),
        );
      }

      if (ok) {
        widget.onUnlocked?.call();
      } else if (mounted) {
        setState(() {
          _localError = store.authError ??
              'Biometrische Anmeldung wurde nicht bestätigt.';
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _localError = 'Biometrische Anmeldung konnte nicht verwendet werden.';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _authenticating = false);
      }
    }
  }

  Future<void> _usePasswordInstead() async {
    widget.onUnlocked?.call();
    await AppStoreScope.of(context).usePasswordInstead();
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final error = _localError ?? store.authError;
    final busy = _authenticating || store.isBiometricAuthenticating;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'FLAPAMAMAKU',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF191B1E),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: const Color(0x18FFFFFF)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(
                      Icons.fingerprint_rounded,
                      size: 76,
                      color: FlapBrand.gold,
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'App entsperren',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w900,
                          ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Mit Fingerabdruck, Gesichtserkennung oder Geräte-PIN entsperren.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white70, height: 1.4),
                    ),
                    if (error != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        error,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                    const SizedBox(height: 18),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: FlapBrand.burgundy,
                        foregroundColor: Colors.white,
                        minimumSize: const Size.fromHeight(52),
                      ),
                      onPressed: busy ? null : _authenticate,
                      icon: busy
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.fingerprint),
                      label: const Text(
                        'Biometrisch entsperren',
                        style: TextStyle(fontWeight: FontWeight.w900),
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: busy ? null : _usePasswordInstead,
                      child: const Text(
                        'Mit Benutzername und Passwort anmelden',
                        style: TextStyle(color: FlapBrand.gold),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
