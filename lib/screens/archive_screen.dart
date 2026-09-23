import 'package:flutter/material.dart';

class ArchiveScreen extends StatelessWidget {
  const ArchiveScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const entries = [
      ArchiveEntry(
        title: 'Schweine Rocker',
        subtitle: 'Fasnachts-Sujet',
        image: 'assets/images/year_motto_pig_rockers.jpg',
      ),
      ArchiveEntry(
        title: 'Zylinder',
        subtitle: 'Früheres Fasnachts-Sujet',
        image: 'assets/images/archive_top_hats_night.jpg',
      ),
      ArchiveEntry(
        title: 'Zylinder Gruppe',
        subtitle: 'Fasnachts-Erinnerung',
        image: 'assets/images/archive_top_hats_barrel.jpg',
      ),
      ArchiveEntry(
        title: 'Wikinger',
        subtitle: 'Früheres Fasnachts-Sujet',
        image: 'assets/images/archive_vikings_bar.jpg',
      ),
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
          childAspectRatio: .82,
        ),
        itemBuilder: (_, i) {
          final entry = entries[i];
          return InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => ArchiveGalleryScreen(entry: entry),
              ),
            ),
            child: Card(
              clipBehavior: Clip.antiAlias,
              margin: EdgeInsets.zero,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Image.asset(
                      entry.image,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          entry.title,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          entry.subtitle,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
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

class ArchiveGalleryScreen extends StatelessWidget {
  final ArchiveEntry entry;

  const ArchiveGalleryScreen({required this.entry, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text(entry.title)),
      body: InteractiveViewer(
        minScale: 1,
        maxScale: 4,
        child: Center(
          child: Image.asset(
            entry.image,
            width: double.infinity,
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}

class ArchiveEntry {
  final String title;
  final String subtitle;
  final String image;

  const ArchiveEntry({
    required this.title,
    required this.subtitle,
    required this.image,
  });
}
