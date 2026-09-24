import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';

class RemoteContentScreen extends StatelessWidget {
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

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final items = store.contentFor(section);

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: items.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(height: 80),
                  Icon(
                    icon,
                    size: 64,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 18),
                  Text(
                    emptyText,
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
                    onDelete: store.canEditContentSection(section)
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
