import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';

enum _ContentSort { newest, oldest, titleAsc, titleDesc }

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

  bool get _isVisualSection =>
      widget.section == 'photos' ||
      widget.section == 'archive' ||
      widget.section == 'sujet';

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
        content: Text('„${item.title}“ wird inklusive Bilder gelöscht.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Löschen'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await store.deleteContentItem(item);
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

  List<String> _images(ContentItem item) {
    if (item.imageUrls.isNotEmpty) {
      return item.imageUrls.where((url) => url.trim().isNotEmpty).toList();
    }
    if (item.imageUrl.trim().isNotEmpty) return [item.imageUrl];
    return const [];
  }

  void _openAlbum(BuildContext context, ContentItem item, int initialIndex) {
    final urls = _images(item);
    if (urls.isEmpty) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _ImageViewerScreen(
          title: item.title,
          urls: urls,
          initialIndex: initialIndex,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final items = _sortedItems(store.contentFor(widget.section));

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: Text(
          widget.title,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          PopupMenuButton<_ContentSort>(
            tooltip: 'Sortieren',
            icon: const Icon(Icons.sort_rounded),
            initialValue: sort,
            onSelected: (value) => setState(() => sort = value),
            itemBuilder: (context) => _ContentSort.values
                .map(
                  (value) => PopupMenuItem(
                    value: value,
                    child: Text(_sortLabel(value)),
                  ),
                )
                .toList(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: items.isEmpty
            ? _EmptyState(icon: widget.icon, text: widget.emptyText)
            : _isVisualSection
                ? _VisualAlbumList(
                    items: items,
                    headers: store.api.authHeaders,
                    onOpen: (item) => _openAlbum(context, item, 0),
                    onDelete: store.canEditContentSection(widget.section)
                        ? (item) => _deleteItem(context, store, item)
                        : null,
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                    itemCount: items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, index) {
                      final item = items[index];
                      return _MockupContentCard(
                        item: item,
                        icon: widget.icon,
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

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String text;

  const _EmptyState({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(30),
      children: [
        const SizedBox(height: 100),
        Container(
          width: 76,
          height: 76,
          margin: const EdgeInsets.symmetric(horizontal: 110),
          decoration: BoxDecoration(
            color: FlapBrand.burgundy,
            borderRadius: BorderRadius.circular(22),
          ),
          child: Icon(icon, size: 38, color: Colors.white),
        ),
        const SizedBox(height: 20),
        Text(
          text,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 17,
            height: 1.4,
          ),
        ),
      ],
    );
  }
}

class _VisualAlbumList extends StatelessWidget {
  final List<ContentItem> items;
  final Map<String, String> headers;
  final ValueChanged<ContentItem> onOpen;
  final ValueChanged<ContentItem>? onDelete;

  const _VisualAlbumList({
    required this.items,
    required this.headers,
    required this.onOpen,
    this.onDelete,
  });

  List<String> _images(ContentItem item) {
    if (item.imageUrls.isNotEmpty) {
      return item.imageUrls.where((url) => url.trim().isNotEmpty).toList();
    }
    if (item.imageUrl.trim().isNotEmpty) return [item.imageUrl];
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 18),
      itemBuilder: (_, index) {
        final item = items[index];
        final urls = _images(item);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            GestureDetector(
              onTap: urls.isEmpty ? null : () => onOpen(item),
              child: Stack(
                children: [
                  AspectRatio(
                    aspectRatio: 4 / 3,
                    child: urls.isNotEmpty
                        ? Image.network(
                            urls.first,
                            headers: headers,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: const Color(0xFF24272B),
                              alignment: Alignment.center,
                              child: const Icon(
                                Icons.broken_image_outlined,
                                color: Colors.white54,
                                size: 50,
                              ),
                            ),
                          )
                        : Container(
                            color: const Color(0xFF24272B),
                            alignment: Alignment.center,
                            child: const Icon(
                              Icons.photo_library_outlined,
                              color: Colors.white54,
                              size: 50,
                            ),
                          ),
                  ),
                  if (urls.isNotEmpty)
                    Positioned(
                      right: 14,
                      bottom: 14,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 11,
                          vertical: 7,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xCC000000),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.zoom_in_rounded,
                              color: Colors.white,
                              size: 18,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              '${urls.length}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      children: [
                        if (item.title.trim().isNotEmpty)
                          Text(
                            item.title.trim(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        if (item.text.trim().isNotEmpty) ...[
                          const SizedBox(height: 7),
                          Text(
                            item.text.trim(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 15,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (onDelete != null)
                    IconButton(
                      tooltip: 'Löschen',
                      color: Colors.white54,
                      onPressed: () => onDelete!(item),
                      icon: const Icon(Icons.delete_outline_rounded),
                    ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _MockupContentCard extends StatelessWidget {
  final ContentItem item;
  final IconData icon;
  final VoidCallback? onOpenLink;
  final VoidCallback? onDelete;

  const _MockupContentCard({
    required this.item,
    required this.icon,
    this.onOpenLink,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF191B1E),
      borderRadius: BorderRadius.circular(18),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 10, 14),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: FlapBrand.burgundy,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: Colors.white),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 16,
                    ),
                  ),
                  if (item.text.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      item.text,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white60),
                    ),
                  ],
                ],
              ),
            ),
            if (onOpenLink != null)
              IconButton(
                tooltip: 'Öffnen',
                color: FlapBrand.gold,
                onPressed: onOpenLink,
                icon: const Icon(Icons.open_in_new_rounded),
              ),
            if (onDelete != null)
              IconButton(
                tooltip: 'Löschen',
                color: Colors.white54,
                onPressed: onDelete,
                icon: const Icon(Icons.delete_outline_rounded),
              ),
          ],
        ),
      ),
    );
  }
}

class _ImageViewerScreen extends StatefulWidget {
  final String title;
  final List<String> urls;
  final int initialIndex;

  const _ImageViewerScreen({
    required this.title,
    required this.urls,
    required this.initialIndex,
  });

  @override
  State<_ImageViewerScreen> createState() => _ImageViewerScreenState();
}

class _ImageViewerScreenState extends State<_ImageViewerScreen> {
  late final PageController _controller;
  late int index;
  bool sharing = false;

  @override
  void initState() {
    super.initState();
    index = widget.initialIndex;
    _controller = PageController(initialPage: index);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _extension(String mimeType) {
    switch (mimeType) {
      case 'image/png':
        return 'png';
      case 'image/webp':
        return 'webp';
      case 'image/gif':
        return 'gif';
      default:
        return 'jpg';
    }
  }

  String _safeName(String value) {
    final cleaned = value
        .replaceAll(RegExp(r'[^A-Za-z0-9ÄÖÜäöü_-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    return cleaned.isEmpty ? 'FLAPAMAMAKU' : cleaned;
  }

  Future<void> _shareCurrent() async {
    if (sharing) return;
    setState(() => sharing = true);
    final store = AppStoreScope.of(context);
    try {
      final downloaded = await store.api.downloadImage(widget.urls[index]);
      final extension = _extension(downloaded.mimeType);
      final filename = '${_safeName(widget.title)}_${index + 1}.$extension';
      await SharePlus.instance.share(
        ShareParams(
          title: 'Bild speichern oder teilen',
          files: [
            XFile.fromData(
              downloaded.bytes,
              mimeType: downloaded.mimeType,
            ),
          ],
          fileNameOverrides: [filename],
        ),
      );
    } finally {
      if (mounted) setState(() => sharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final headers = AppStoreScope.of(context).api.authHeaders;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.title,
              style: const TextStyle(fontWeight: FontWeight.w900),
            ),
            Text(
              '${index + 1} / ${widget.urls.length}',
              style: const TextStyle(
                color: Colors.white54,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Speichern / Teilen',
            onPressed: sharing ? null : _shareCurrent,
            icon: sharing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.ios_share_rounded),
          ),
        ],
      ),
      body: Stack(
        children: [
          PageView.builder(
            controller: _controller,
            itemCount: widget.urls.length,
            onPageChanged: (value) => setState(() => index = value),
            itemBuilder: (_, imageIndex) => InteractiveViewer(
              minScale: 1,
              maxScale: 5,
              child: Center(
                child: Image.network(
                  widget.urls[imageIndex],
                  headers: headers,
                  width: double.infinity,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const Center(
                    child: Text(
                      'Bild konnte nicht geladen werden.',
                      style: TextStyle(color: Colors.white70),
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (widget.urls.length > 1)
            Positioned(
              left: 0,
              right: 0,
              bottom: 24,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  widget.urls.length,
                  (i) => AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: i == index ? 22 : 7,
                    height: 7,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      color: i == index ? FlapBrand.gold : Colors.white38,
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
