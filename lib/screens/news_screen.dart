import 'package:flutter/material.dart';
import '../data/app_store.dart';
import 'content_detail_screens.dart';

class NewsScreen extends StatelessWidget {
  const NewsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final items = store.news;

    return Scaffold(
      appBar: AppBar(title: const Text('News')),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (_, i) {
          final item = items[i];
          return Card(
            child: ListTile(
              leading: const CircleAvatar(child: Icon(Icons.article_outlined)),
              title: Text(
                item.title,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Text('${item.date}\n${item.text}'),
              isThreeLine: true,
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => NewsDetailScreen(item: item),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
