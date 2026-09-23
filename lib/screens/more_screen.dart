import 'package:flutter/material.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const items = [
      (Icons.description_outlined, 'Dokumente', 'Protokolle, Reglemente, Infos'),
      (Icons.photo_album_outlined, 'Fotoalben', 'Bilder von Anlässen und Umzügen'),
      (Icons.how_to_vote_outlined, 'Umfragen', 'Mitreden und mitgestalten'),
      (Icons.link, 'Links', 'Nützliche Webseiten'),
      (Icons.mail_outline, 'Kontakt', 'Fragen oder Anliegen'),
      (Icons.settings_outlined, 'Einstellungen', 'Benachrichtigungen und Datenschutz'),
      (Icons.info_outline, 'Über uns', 'Unsere Geschichte'),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Mehr')),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (_, i) {
          final item = items[i];
          return Card(child: ListTile(
            leading: Icon(item.$1, color: Theme.of(context).colorScheme.primary),
            title: Text(item.$2, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(item.$3),
            trailing: const Icon(Icons.chevron_right),
          ));
        },
      ),
    );
  }
}
