import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';
import 'password_change_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const String appVersion = String.fromEnvironment(
    'APP_VERSION',
    defaultValue: '0.8.19',
  );
  static const String buildNumber = String.fromEnvironment(
    'APP_BUILD_NUMBER',
    defaultValue: '34',
  );

  Future<void> _chooseClub(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final selected = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: const Color(0xFF191B1E),
      builder: (context) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: [
            const ListTile(
              title: Text(
                'Verein wechseln',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  fontSize: 18,
                ),
              ),
            ),
            for (final club in store.accessibleClubs)
              ListTile(
                leading: Icon(
                  club['current'] == true
                      ? Icons.check_circle_rounded
                      : Icons.groups_rounded,
                  color: club['current'] == true
                      ? FlapBrand.gold
                      : Colors.white70,
                ),
                title: Text(
                  club['name']?.toString() ?? 'Verein',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                subtitle: (club['short_name']?.toString() ?? '').isEmpty
                    ? null
                    : Text(
                        club['short_name'].toString(),
                        style: const TextStyle(color: Colors.white54),
                      ),
                onTap: () {
                  final rawId = club['id'];
                  final id = rawId is int
                      ? rawId
                      : int.tryParse(rawId?.toString() ?? '');
                  if (id != null) Navigator.of(context).pop(id);
                },
              ),
          ],
        ),
      ),
    );
    if (selected == null || selected == store.currentClubId) return;
    final ok = await store.selectClub(selected);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            store.authError ?? 'Verein konnte nicht gewechselt werden.',
          ),
        ),
      );
    } else if (context.mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Einstellungen',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
        children: [
          const _SectionTitle('SICHERHEIT'),
          const SizedBox(height: 10),
          const _SettingsCard(
            child: ListTile(
              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: Icon(
                Icons.verified_user_rounded,
                color: FlapBrand.gold,
                size: 29,
              ),
              title: Text(
                'Dauerhaft angemeldet',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              subtitle: Text(
                'Die Anmeldung bleibt auf diesem Gerät aktiv, bis du dich bewusst abmeldest oder ein Administrator die Sitzung beendet.',
                style: TextStyle(color: Colors.white60),
              ),
            ),
          ),
          const SizedBox(height: 10),
          _SettingsCard(
            child: SwitchListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              secondary: const Icon(
                Icons.fingerprint_rounded,
                color: FlapBrand.gold,
                size: 29,
              ),
              title: const Text(
                'Biometrische Anmeldung',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
              ),
              subtitle: Text(
                store.biometricEnabled
                    ? 'Biometrische Wiederanmeldung ist auf diesem Gerät aktiviert'
                    : 'Fingerabdruck, Gesichtserkennung oder Geräte-PIN verwenden',
                style: const TextStyle(color: Colors.white60),
              ),
              value: store.biometricEnabled,
              activeThumbColor: Colors.white,
              activeTrackColor: store.themeColor,
              onChanged: (value) async {
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
            ),
          ),
          const SizedBox(height: 10),
          _SettingsCard(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: const Icon(
                Icons.password_rounded,
                color: FlapBrand.gold,
                size: 29,
              ),
              title: const Text(
                'Passwort ändern',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
              ),
              subtitle: const Text(
                'Eigenes Passwort jederzeit ändern · mindestens 8 Zeichen',
                style: TextStyle(color: Colors.white60),
              ),
              trailing: const Icon(Icons.chevron_right_rounded, color: Colors.white54),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const PasswordChangeScreen()),
              ),
            ),
          ),
          if (store.canSwitchClub) ...[
            const SizedBox(height: 22),
            const _SectionTitle('VEREIN'),
            const SizedBox(height: 10),
            _SettingsCard(
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                leading: const Icon(
                  Icons.groups_rounded,
                  color: FlapBrand.gold,
                  size: 29,
                ),
                title: Text(
                  store.currentClubName,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                ),
                subtitle: Text(
                  store.isSuperAdmin
                      ? 'Super-Admin · Verein wechseln'
                      : 'Verein wechseln',
                  style: const TextStyle(color: Colors.white60),
                ),
                trailing: const Icon(Icons.swap_horiz_rounded, color: Colors.white70),
                onTap: () => _chooseClub(context),
              ),
            ),
          ],
          const SizedBox(height: 22),
          const _SectionTitle('BENACHRICHTIGUNGEN'),
          const SizedBox(height: 10),
          _SettingsCard(
            child: SwitchListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              secondary: const Icon(
                Icons.notifications_active_rounded,
                color: FlapBrand.gold,
                size: 29,
              ),
              title: const Text(
                'Push-Benachrichtigungen',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
              ),
              subtitle: Text(
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
              value: store.pushEnabled,
              activeThumbColor: Colors.white,
              activeTrackColor: store.themeColor,
              onChanged: (value) async {
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
            ),
          ),
          const SizedBox(height: 26),
          Center(
            child: Text(
              'Version $appVersion',
              style: const TextStyle(
                color: Colors.white38,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: FlapBrand.gold,
        fontWeight: FontWeight.w900,
        fontSize: 11,
        letterSpacing: 1.5,
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  final Widget child;
  const _SettingsCard({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0x18FFFFFF)),
      ),
      child: child,
    );
  }
}
