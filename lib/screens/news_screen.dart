import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import 'content_detail_screens.dart';

class NewsScreen extends StatelessWidget {
  const NewsScreen({super.key});

  Widget? _newsImage(NewsItem item, Map<String, String> headers) {
    if (item.imageUrl.isNotEmpty) {
      return AspectRatio(
        aspectRatio: 16 / 9,
        child: Image.network(
          item.imageUrl,
          headers: headers,
          width: double.infinity,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => const SizedBox.shrink(),
        ),
      );
    }

    if (item.imageAsset.isNotEmpty) {
      return AspectRatio(
        aspectRatio: 16 / 9,
        child: Image.asset(
          item.imageAsset,
          width: double.infinity,
          fit: BoxFit.cover,
        ),
      );
    }

    return null;
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final items = store.news;

    return Scaffold(
      appBar: AppBar(title: const Text('News')),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: items.isEmpty
            ? const ListView(
                physics: AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.all(24),
                children: [
                  SizedBox(height: 120),
                  Center(child: Text('Noch keine News vorhanden')),
                ],
              )
            : ListView.separated(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(height: 14),
                itemBuilder: (_, i) {
                  final item = items[i];
                  final image = _newsImage(item, store.api.authHeaders);

                  return Card(
                    clipBehavior: Clip.antiAlias,
                    margin: EdgeInsets.zero,
                    child: InkWell(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => NewsDetailScreen(item: item),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (image != null) image,
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.date,
                                  style: TextStyle(
                                    color:
                                        Theme.of(context).colorScheme.primary,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  item.title,
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleLarge
                                      ?.copyWith(fontWeight: FontWeight.w800),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  item.text,
                                  maxLines: 4,
                                  overflow: TextOverflow.ellipsis,
                                  style:
                                      Theme.of(context).textTheme.bodyLarge,
                                ),
                                const SizedBox(height: 8),
                                const Align(
                                  alignment: Alignment.centerRight,
                                  child: Icon(Icons.chevron_right),
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
      ),
    );
  }
}
