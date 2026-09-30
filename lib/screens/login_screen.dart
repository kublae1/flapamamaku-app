import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../widgets/offline_network_image.dart';
import '../theme/flap_brand.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final store = AppStoreScope.of(context);
    if (!store.serverConfigured) {
      await _changeServer();
      return;
    }
    if (_username.text.trim().isEmpty || _password.text.isEmpty) return;
    await store.login(_username.text, _password.text);
  }

  Future<void> _changeServer() async {
    final store = AppStoreScope.of(context);
    final controller = TextEditingController(text: store.serverUrl);
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Vereinsserver'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(
            labelText: 'Serveradresse',
            hintText: 'https://verein.example.ch',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('Verbinden'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (value == null || value.trim().isEmpty) return;

    final ok = await store.changeServerUrl(value);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            store.authError ?? 'Server konnte nicht übernommen werden.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 430),
              child: Column(
                children: [
                  Container(
                    width: 94,
                    height: 94,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: store.appLogoUrl.isNotEmpty
                        ? OfflineNetworkImage(
                            store.appLogoUrl,
                            fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => Image.asset(
                              'assets/FLAPAMAMAKU App-Icon.png',
                              fit: BoxFit.contain,
                            ),
                          )
                        : Image.asset(
                            'assets/FLAPAMAMAKU App-Icon.png',
                            fit: BoxFit.contain,
                          ),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    store.appName,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: store.themeColor,
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.2,
                    ),
                  ),
                  if (store.appSubtitle.isNotEmpty) ...[
                    const SizedBox(height: 5),
                    Text(
                      store.appSubtitle,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: FlapBrand.gold,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                  const SizedBox(height: 30),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: const Color(0xFF191B1E),
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(color: const Color(0x18FFFFFF)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Anmelden',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 20),
                        TextField(
                          controller: _username,
                          style: const TextStyle(color: Colors.white),
                          textInputAction: TextInputAction.next,
                          autofillHints: const [AutofillHints.username],
                          decoration: _decoration(
                            'Benutzername',
                            Icons.person_outline_rounded,
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _password,
                          obscureText: _obscure,
                          style: const TextStyle(color: Colors.white),
                          autofillHints: const [AutofillHints.password],
                          onSubmitted: (_) => _submit(),
                          decoration: _decoration(
                            'Passwort',
                            Icons.lock_outline_rounded,
                          ).copyWith(
                            suffixIcon: IconButton(
                              color: Colors.white54,
                              onPressed: () => setState(() => _obscure = !_obscure),
                              icon: Icon(
                                _obscure
                                    ? Icons.visibility_rounded
                                    : Icons.visibility_off_rounded,
                              ),
                            ),
                          ),
                        ),
                        if (store.authError != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            store.authError!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Color(0xFFFF6B6B),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                        const SizedBox(height: 18),
                        SizedBox(
                          height: 52,
                          child: FilledButton(
                            style: FilledButton.styleFrom(
                              backgroundColor: store.themeColor,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            onPressed: store.isAuthenticating ? null : _submit,
                            child: store.isAuthenticating
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text(
                                    'Anmelden',
                                    style: TextStyle(
                                      fontWeight: FontWeight.w900,
                                      fontSize: 16,
                                    ),
                                  ),
                          ),
                        ),
                        if (store.canChangeServer) ...[
                          const SizedBox(height: 14),
                          TextButton.icon(
                            onPressed: _changeServer,
                            icon: const Icon(Icons.dns_outlined),
                            label: Text(
                              store.serverConfigured
                                  ? 'Vereinsserver wechseln'
                                  : 'Vereinsserver einrichten',
                            ),
                          ),
                          if (store.serverConfigured) ...[
                            const SizedBox(height: 2),
                            Text(
                              store.serverUrl,
                              textAlign: TextAlign.center,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white38,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ],
                        const SizedBox(height: 16),
                        const Row(
                          children: [
                            Expanded(
                              child: Divider(color: Color(0x33FFFFFF)),
                            ),
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 12),
                              child: Text(
                                'oder',
                                style: TextStyle(color: Colors.white54),
                              ),
                            ),
                            Expanded(
                              child: Divider(color: Color(0x33FFFFFF)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 52,
                          child: OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.white,
                              side: const BorderSide(color: FlapBrand.gold),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            onPressed: store.isBiometricAuthenticating
                                ? null
                                : store.loginWithBiometrics,
                            icon: store.isBiometricAuthenticating
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Icon(Icons.fingerprint_rounded),
                            label: const Text(
                              'Biometrisch anmelden',
                              style: TextStyle(fontWeight: FontWeight.w900),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _decoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Colors.white60),
      prefixIcon: Icon(icon, color: FlapBrand.gold),
      filled: true,
      fillColor: const Color(0xFF111315),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: Color(0x33FFFFFF)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: FlapBrand.gold, width: 1.3),
      ),
    );
  }
}
