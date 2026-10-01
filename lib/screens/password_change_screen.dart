import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

class PasswordChangeScreen extends StatefulWidget {
  final bool forced;

  const PasswordChangeScreen({this.forced = false, super.key});

  @override
  State<PasswordChangeScreen> createState() => _PasswordChangeScreenState();
}

class _PasswordChangeScreenState extends State<PasswordChangeScreen> {
  final current = TextEditingController();
  final next = TextEditingController();
  final confirm = TextEditingController();
  bool saving = false;
  bool obscureCurrent = true;
  bool obscureNext = true;

  @override
  void dispose() {
    current.dispose();
    next.dispose();
    confirm.dispose();
    super.dispose();
  }

  Future<void> save() async {
    final store = AppStoreScope.of(context);
    if (next.text.length < 8) {
      _message('Das neue Passwort muss mindestens 8 Zeichen haben.');
      return;
    }
    if (next.text != confirm.text) {
      _message('Die neuen Passwörter stimmen nicht überein.');
      return;
    }
    setState(() => saving = true);
    final ok = await store.changePassword(current.text, next.text);
    if (!mounted) return;
    setState(() => saving = false);
    if (!ok) {
      _message(store.authError ?? 'Passwort konnte nicht geändert werden.');
      return;
    }
    _message('Passwort wurde geändert.');
    if (!widget.forced) Navigator.of(context).pop();
  }

  void _message(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: widget.forced ? null : AppBar(title: const Text('Passwort ändern')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 430),
              child: Card(
                color: const Color(0xFF191B1E),
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        widget.forced
                            ? 'Passwort beim ersten Login ändern'
                            : 'Passwort ändern',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 23,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      if (widget.forced)
                        const Text(
                          'Das temporäre Passwort muss vor der weiteren Nutzung der App ersetzt werden.',
                          style: TextStyle(color: Colors.white60),
                        ),
                      const SizedBox(height: 20),
                      TextField(
                        controller: current,
                        obscureText: obscureCurrent,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          labelText: 'Aktuelles / temporäres Passwort',
                          suffixIcon: IconButton(
                            onPressed: () => setState(() => obscureCurrent = !obscureCurrent),
                            icon: Icon(obscureCurrent ? Icons.visibility : Icons.visibility_off),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: next,
                        obscureText: obscureNext,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          labelText: 'Neues Passwort',
                          helperText: 'Mindestens 8 Zeichen',
                          suffixIcon: IconButton(
                            onPressed: () => setState(() => obscureNext = !obscureNext),
                            icon: Icon(obscureNext ? Icons.visibility : Icons.visibility_off),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: confirm,
                        obscureText: true,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(
                          labelText: 'Neues Passwort bestätigen',
                        ),
                      ),
                      const SizedBox(height: 20),
                      FilledButton(
                        onPressed: saving ? null : save,
                        style: FilledButton.styleFrom(
                          backgroundColor: store.themeColor,
                          minimumSize: const Size.fromHeight(50),
                        ),
                        child: saving
                            ? const CircularProgressIndicator(strokeWidth: 2)
                            : const Text('Passwort speichern'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
