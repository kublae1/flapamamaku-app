import 'package:flutter/material.dart';
import '../models/app_data.dart';
import '../widgets/section_title.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverAppBar(
          expandedHeight: 240,
          pinned: true,
          backgroundColor: const Color(0xFF8A101B),
          title: const Text('FLAPAMAMAKU'),
          flexibleSpace: FlexibleSpaceBar(
            background: Container(
              padding: const EdgeInsets.fromLTRB(24, 88, 24, 24),
              decoration: const BoxDecoration(
                gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF8A101B), Color(0xFF3A0810)]),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text('Fasnachtsgruppe Luzern', style: TextStyle(color: Colors.white70, fontSize: 16)),
                  SizedBox(height: 8),
                  Text('Zäme dur d\'Fasnacht!', style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800)),
                ],
              ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.all(16),
          sliver: SliverList.list(children: [
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
            ...eventItems.take(2).map((e) => Card(
              child: ListTile(
                leading: SizedBox(width: 48, child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text(e.day, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)), Text(e.month)])),
                title: Text(e.title),
                subtitle: Text('${e.location} · ${e.time}'),
                trailing: const Icon(Icons.chevron_right),
              ),
            )),
            const SizedBox(height: 12),
          ]),
        ),
      ],
    );
  }
}
