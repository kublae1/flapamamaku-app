import 'package:flutter/material.dart';
import '../data/app_store.dart';
import 'year_motto_screen.dart';
import 'archive_screen.dart';
import 'content_detail_screens.dart';
import 'admin_screen.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Mehr')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (store.canAdminister)
            _menuItem(
              context,
              Icons.admin_panel_settings_outlined,
              'Administration',
              'Nur freigegebene Bereiche verwalten',
              () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AdminScreen()),
              ),
            ),
          if (store.serverConfigured && store.isAuthenticated)
            Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.account_circle_outlined),
                    title: Text(
                      store.signedInName.isEmpty
                          ? 'Angemeldet'
                          : store.signedInName,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: const Text('Benutzerkonto'),
                    trailing: TextButton.icon(
                      onPressed: store.logout,
                      icon: const Icon(Icons.logout),
                      label: const Text('Abmelden'),
                    ),
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    secondary: const Icon(Icons.fingerprint),
                    title: const Text('Biometrische Anmeldung'),
                    subtitle: Text(
                      store.biometricEnabled
                          ? 'Beim App-Start mit Fingerabdruck, Gesicht oder Geräte-PIN entsperren'
                          : 'Schnelles und sicheres Entsperren aktivieren',
                    ),
                    value: store.biometricEnabled,
                    onChanged: (value) async {
                      final ok = await store.setBiometricEnabled(value);
                      if (!ok && context.mounted && store.authError != null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(store.authError!)),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),
          _menuItem(
            context,
            Icons.auto_awesome_outlined,
            'Aktuelles Sujet',
            'Fotos und aktuelles Fasnachtssujet',
            () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const YearMottoScreen()),
            ),
          ),
          _menuItem(
            context,
            Icons.history,
            'Archiv',
            'Frühere Mottos, Sujets und Bilder',
            () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ArchiveScreen()),
            ),
          ),
          _section(
            context,
            Icons.description_outlined,
            'Dokumente',
            'Protokolle, Reglemente und interne Informationen.',
          ),
          _section(
            context,
            Icons.photo_album_outlined,
            'Fotoalben',
            'Fotoalben von Anlässen, Umzügen und gemeinsamen Aktivitäten.',
          ),
          _section(
            context,
            Icons.how_to_vote_outlined,
            'Umfragen',
            'Interne Umfragen und Abstimmungen der Gruppe.',
          ),
          _section(
            context,
            Icons.link,
            'Links',
            'Nützliche Webseiten und Verweise der Fasnachtsgruppe.',
          ),
          _section(
            context,
            Icons.mail_outline,
            'Kontakt',
            'Kontaktinformationen und Ansprechpersonen.',
          ),
          _section(
            context,
            Icons.settings_outlined,
            'Einstellungen',
            'Benachrichtigungen, Datenschutz und App-Einstellungen.',
          ),
          _section(
            context,
            Icons.info_outline,
            'Über uns',
            'Informationen über FLAPAMAMAKU und die Geschichte der Gruppe.',
          ),
        ],
      ),
    );
  }

  Widget _section(
    BuildContext context,
    IconData icon,
    String title,
    String description,
  ) {
    return _menuItem(
      context,
      icon,
      title,
      description,
      () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => SimpleSectionScreen(
            title: title,
            description: description,
            icon: icon,
          ),
        ),
      ),
    );
  }

  Widget _menuItem(
    BuildContext context,
    IconData icon,
    String title,
    String subtitle,
    VoidCallback onTap,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
