import 'package:flutter/material.dart';
import '../models/app_data.dart';
import '../widgets/section_title.dart';
import 'year_motto_screen.dart';
import 'archive_screen.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverAppBar(
          expandedHeight: 285,
          pinned: true,
          backgroundColor: const Color(0xFF8A101B),
          title: const Text('FLAPAMAMAKU'),
          flexibleSpace: FlexibleSpaceBar(
            background: Stack(
              fit: StackFit.expand,
              children: [
                Image.asset(
                  'assets/images/hero_fireworks.jpg',
                  fit: BoxFit.cover,
                ),
                const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Colors.black12, Colors.black87],
                    ),
                  ),
                ),
                const Positioned(
                  left: 22,
                  right: 22,
                  bottom: 22,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Fasnachtsgruppe Luzern',
                        style: TextStyle(color: Colors.white70, fontSize: 16),
                      ),
                      SizedBox(height: 5),
                      Text(
                        'Zäme dur d\'Fasnacht!',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 29,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
          sliver: SliverList.list(
            children: [
              const SectionTitle('Jahresmotto'),
              const SizedBox(height: 10),
              InkWell(
                borderRadius: BorderRadius.circular(18),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                ),
                child: Card(
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      AspectRatio(
                        aspectRatio: 16 / 9,
                        child: Image.asset(
                          'assets/images/year_motto_pig_rockers.jpg',
                          fit: BoxFit.cover,
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Jahresmotto folgt',
                                    style: TextStyle(
                                      fontSize: 19,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  SizedBox(height: 4),
                                  Text(
                                    'Aktuelles Sujet und Informationen zur Fasnacht.',
                                  ),
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_right),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 22),
              const SectionTitle('Aktuelle News', action: 'Alle'),
              const SizedBox(height: 8),
              Card(
                child: ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.campaign)),
                  title: Text(newsItems.first.title),
                  subtitle: Text('${newsItems.first.date}\n${newsItems.first.text}'),
                  isThreeLine: true,
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
              const SizedBox(height: 20),
              const SectionTitle('Nächste Termine', action: 'Alle'),
              const SizedBox(height: 8),
              ...eventItems.take(2).map(
                (e) => Card(
                  child: ListTile(
                    leading: SizedBox(
                      width: 48,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            e.day,
                            style: const TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(e.month),
                        ],
                      ),
                    ),
                    title: Text(e.title),
                    subtitle: Text('${e.location} · ${e.time}'),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Card(
                child: ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.history)),
                  title: const Text(
                    'Archiv',
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: const Text('Frühere Mottos, Sujets und Erinnerungen'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ArchiveScreen()),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
