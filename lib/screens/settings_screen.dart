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
          const SizedBox(height: 22),
          const Text(
            'BENACHRICHTIGUNGEN',
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
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 4,
              ),
              secondary: const Icon(
                Icons.notifications_active_rounded,
                color: FlapBrand.gold,
                size: 29,
              ),
              title: const Text(
                'Push-Benachrichtigungen',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              subtitle: Text(
                store.pushAvailable
                    ? 'Neue News sowie neue oder geänderte Termine auf dem Handy anzeigen'
                    : 'Push-Dienst wird vorbereitet und nach Firebase-Einrichtung verfügbar',
                style: const TextStyle(color: Colors.white60),
              ),
              value: store.pushEnabled,
              activeThumbColor: Colors.white,
              activeTrackColor: store.themeColor,
              onChanged: store.pushAvailable
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
