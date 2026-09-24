import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';

enum _ContentSort {
  newest,
  oldest,
  titleAsc,
  titleDesc,
}

class RemoteContentScreen extends StatefulWidget {
  final String section;
  final String title;
  final String emptyText;
  final IconData icon;

  const RemoteContentScreen({
    required this.section,
    required this.title,
    required this.emptyText,
    required this.icon,
    super.key,
  });

  @override
  State<RemoteContentScreen> createState() => _RemoteContentScreenState();
}

class _RemoteContentScreenState extends State<RemoteContentScreen> {
  _ContentSort sort = _ContentSort.newest;

  Future<void> _openLink(BuildContext context, String value) async {
    final uri = Uri.tryParse(value);
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Link konnte nicht geöffnet werden.')),
      );
    }
  }

  Future<void> _deleteItem(
    BuildContext context,
    AppStore store,
    ContentItem item,
  ) async {
    if (item.id == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Eintrag löschen?'),
        content: Text(
          '„${item.title}“ wird inklusive zugehöriger Bilder gelöscht.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Abbrechen'),
          ),
          FilledButton.tonalIcon(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Löschen'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await store.deleteContentItem(item);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Eintrag gelöscht.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Eintrag konnte nicht gelöscht werden.')),
        );
      }
    }
  }

  List<ContentItem> _sortedItems(List<ContentItem> source) {
    final items = List<ContentItem>.from(source);
    switch (sort) {
      case _ContentSort.newest:
        items.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      case _ContentSort.oldest:
        items.sort((a, b) => a.createdAt.compareTo(b.createdAt));
      case _ContentSort.titleAsc:
        items.sort(
          (a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()),
        );
      case _ContentSort.titleDesc:
        items.sort(
          (a, b) => b.title.toLowerCase().compareTo(a.title.toLowerCase()),
        );
    }
    return items;
  }

  String _sortLabel(_ContentSort value) {
    switch (value) {
      case _ContentSort.newest:
        return 'Neueste zuerst';
      case _ContentSort.oldest:
        return 'Älteste zuerst';
      case _ContentSort.titleAsc:
        return 'Titel A–Z';
      case _ContentSort.titleDesc:
        return 'Titel Z–A';
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final items = _sortedItems(store.contentFor(widget.section));

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        actions: [
          PopupMenuButton<_ContentSort>(
            tooltip: 'Sortieren',
            icon: const Icon(Icons.sort),
            initialValue: sort,
            onSelected: (value) => setState(() => sort = value),
            itemBuilder: (context) => _ContentSort.values
                .map(
                  (value) => PopupMenuItem<_ContentSort>(
                    value: value,
                    child: Row(
                      children: [
                        if (value == sort) ...[
                          const Icon(Icons.check, size: 18),
                          const SizedBox(width: 8),
                        ],
                        Text(_sortLabel(value)),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: items.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(height: 80),
                  Icon(
                    widget.icon,
                    size: 64,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 18),
                  Text(
                    widget.emptyText,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ],
              )
            : ListView.separated(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (_, index) {
                  final item = items[index];
                  return _ContentCard(
                    item: item,
                    headers: store.api.authHeaders,
                    onOpenLink: item.linkUrl.isEmpty
                        ? null
                        : () => _openLink(context, item.linkUrl),
                    onDelete: store.canEditContentSection(widget.section)
                        ? () => _deleteItem(context, store, item)
                        : null,
                  );
                },
              ),
      ),
    );
  }
}

class _ContentCard extends StatelessWidget {
  final ContentItem item;
  final Map<String, String> headers;
  final VoidCallback? onOpenLink;
  final VoidCallback? onDelete;

  const _ContentCard({
    required this.item,
    required this.headers,
    this.onOpenLink,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (item.imageUrls.isNotEmpty)
            SizedBox(
              height: 220,
              child: ListView.separated(
                padding: const EdgeInsets.all(8),
                scrollDirection: Axis.horizontal,
                itemCount: item.imageUrls.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, index) => ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Image.network(
                    item.imageUrls[index],
                    headers: headers,
                    width: 280,
                    height: 220,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                  ),
                ),
              ),
            )
          else if (item.imageUrl.isNotEmpty)
            Image.network(
              item.imageUrl,
              headers: headers,
              width: double.infinity,
              height: 210,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                if (item.text.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    item.text,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                ],
                if (onOpenLink != null || onDelete != null) ...[
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (onOpenLink != null)
                        OutlinedButton.icon(
                          onPressed: onOpenLink,
                          icon: const Icon(Icons.open_in_new),
                          label: const Text('Öffnen'),
                        ),
                      if (onOpenLink != null && onDelete != null)
                        const SizedBox(width: 8),
                      if (onDelete != null)
                        OutlinedButton.icon(
                          onPressed: onDelete,
                          icon: const Icon(Icons.delete_outline),
                          label: const Text('Löschen'),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
