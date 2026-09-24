import 'package:flutter/material.dart';

import '../data/app_store.dart';
import 'admin_screen.dart';
import 'content_detail_screens.dart';
import 'remote_content_screen.dart';

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
          _remoteSection(
            context,
            section: 'sujet',
            icon: Icons.auto_awesome_outlined,
            title: 'Aktuelles Sujet',
            subtitle: 'Fotos und aktuelles Fasnachtssujet',
            emptyText: 'Noch kein aktuelles Sujet hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'archive',
            icon: Icons.history,
            title: 'Archiv',
            subtitle: 'Frühere Mottos, Sujets und Bilder',
            emptyText: 'Noch keine Archiveinträge hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'documents',
            icon: Icons.description_outlined,
            title: 'Dokumente',
            subtitle: 'Protokolle, Reglemente und interne Informationen.',
            emptyText: 'Noch keine Dokumente hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'photos',
            icon: Icons.photo_album_outlined,
            title: 'Fotoalben',
            subtitle:
                'Fotoalben von Anlässen, Umzügen und gemeinsamen Aktivitäten.',
            emptyText: 'Noch keine Fotoalben hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'polls',
            icon: Icons.how_to_vote_outlined,
            title: 'Umfragen',
            subtitle: 'Interne Umfragen und Abstimmungen der Gruppe.',
            emptyText: 'Noch keine Umfragen hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'links',
            icon: Icons.link,
            title: 'Links',
            subtitle: 'Nützliche Webseiten und Verweise der Fasnachtsgruppe.',
            emptyText: 'Noch keine Links hinterlegt.',
          ),
          _remoteSection(
            context,
            section: 'contact',
            icon: Icons.mail_outline,
            title: 'Kontakt',
            subtitle: 'Kontaktinformationen und Ansprechpersonen.',
            emptyText: 'Noch keine Kontaktinformationen hinterlegt.',
          ),
          _section(
            context,
            Icons.settings_outlined,
            'Einstellungen',
            'Benachrichtigungen, Datenschutz und App-Einstellungen.',
          ),
          _remoteSection(
            context,
            section: 'about',
            icon: Icons.info_outline,
            title: 'Über uns',
            subtitle: 'Informationen über FLAPAMAMAKU und die Geschichte der Gruppe.',
            emptyText: 'Noch keine Informationen hinterlegt.',
          ),
        ],
      ),
    );
  }

  Widget _remoteSection(
    BuildContext context, {
    required String section,
    required IconData icon,
    required String title,
    required String subtitle,
    required String emptyText,
  }) {
    return _menuItem(
      context,
      icon,
      title,
      subtitle,
      () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => RemoteContentScreen(
            section: section,
            title: title,
            emptyText: emptyText,
            icon: icon,
          ),
        ),
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
