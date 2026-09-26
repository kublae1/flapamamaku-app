import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

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
          const Text(
            'SICHERHEIT',
            style: TextStyle(
              color: FlapBrand.gold,
              fontWeight: FontWeight.w900,
              fontSize: 11,
              letterSpacing: 1.5,
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
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              subtitle: Text(
                store.biometricEnabled
                    ? 'Beim App-Start biometrisch entsperren'
                    : 'Fingerabdruck, Gesicht oder Geräte-PIN verwenden',
                style: const TextStyle(color: Colors.white60),
              ),
              value: store.biometricEnabled,
              activeThumbColor: Colors.white,
              activeTrackColor: FlapBrand.burgundy,
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
          const SizedBox(height: 22),
          const Text(
            'APP-INFORMATION',
            style: TextStyle(
              color: FlapBrand.gold,
              fontWeight: FontWeight.w900,
              fontSize: 11,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 10),
          const _SettingsCard(
            child: Column(
              children: [
                _InfoRow(
                  icon: Icons.info_outline_rounded,
                  title: 'App-Version',
                  value: appVersion,
                ),
                Divider(height: 1, color: Color(0x22FFFFFF)),
                _InfoRow(
                  icon: Icons.tag_rounded,
                  title: 'APK-Build',
                  value: buildNumber,
                ),
              ],
            ),
          ),
        ],
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

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: FlapBrand.gold),
      title: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
        ),
      ),
      trailing: Text(
        value,
        style: const TextStyle(
          color: Colors.white70,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
