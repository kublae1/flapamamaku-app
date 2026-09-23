import 'package:flutter/material.dart';

class ArchiveScreen extends StatelessWidget {
  const ArchiveScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const entries = [
      ('2015', 'Jahreslogo', Icons.workspace_premium_outlined),
      ('Zylinder', 'Frühere Fasnachtsbilder', Icons.photo_library_outlined),
      ('Wikinger', 'Sujet und Gruppenbilder', Icons.shield_outlined),
      ('Gruppenfotos', 'Erinnerungen aus vergangenen Jahren', Icons.groups_outlined),
      ('Luzerner Fasnacht', 'Stimmungen und Impressionen', Icons.celebration_outlined),
      ('Weitere Jahre', 'Das Archiv wird laufend ergänzt', Icons.history),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Archiv')),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: entries.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.05,
        ),
        itemBuilder: (_, i) {
          final e = entries[i];
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Icon(e.$3, size: 34),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        e.$1,
                        style: const TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(e.$2),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
