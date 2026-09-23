import 'package:flutter/material.dart';
import 'year_motto_screen.dart';
import 'archive_screen.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mehr')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _menuItem(
            context,
            Icons.auto_awesome_outlined,
            'Jahresmotto',
            'Aktuelles Sujet und Motto',
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
          _menuItem(context, Icons.description_outlined, 'Dokumente', 'Protokolle, Reglemente, Infos', null),
          _menuItem(context, Icons.photo_album_outlined, 'Fotoalben', 'Bilder von Anlässen und Umzügen', null),
          _menuItem(context, Icons.how_to_vote_outlined, 'Umfragen', 'Mitreden und mitgestalten', null),
          _menuItem(context, Icons.link, 'Links', 'Nützliche Webseiten', null),
          _menuItem(context, Icons.mail_outline, 'Kontakt', 'Fragen oder Anliegen', null),
          _menuItem(context, Icons.settings_outlined, 'Einstellungen', 'Benachrichtigungen und Datenschutz', null),
          _menuItem(context, Icons.info_outline, 'Über uns', 'Unsere Geschichte', null),
        ],
      ),
    );
  }

  Widget _menuItem(
    BuildContext context,
    IconData icon,
    String title,
    String subtitle,
    VoidCallback? onTap,
  ) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
