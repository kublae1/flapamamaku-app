import 'package:flutter/material.dart';
import '../models/app_data.dart';

class NewsScreen extends StatelessWidget {
  const NewsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('News')),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: newsItems.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (_, i) {
          final item = newsItems[i];
          return Card(child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.photo_library_outlined)),
            title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('${item.date}\n${item.text}'),
            isThreeLine: true,
            trailing: const Icon(Icons.chevron_right),
          ));
        },
      ),
    );
  }
}
