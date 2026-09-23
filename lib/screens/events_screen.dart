import 'package:flutter/material.dart';
import '../models/app_data.dart';

class EventsScreen extends StatelessWidget {
  const EventsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Termine')),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: eventItems.length,
        itemBuilder: (_, i) {
          final e = eventItems[i];
          return Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ListTile(
              leading: Container(
                width: 54,
                padding: const EdgeInsets.symmetric(vertical: 6),
                decoration: BoxDecoration(border: Border.all(color: Theme.of(context).colorScheme.primary), borderRadius: BorderRadius.circular(10)),
                child: Column(mainAxisSize: MainAxisSize.min, children: [Text(e.day, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)), Text(e.month)]),
              ),
              title: Text(e.title, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('${e.location}\n${e.time}'),
              isThreeLine: true,
              trailing: const Icon(Icons.chevron_right),
            ),
          );
        },
      ),
    );
  }
}
