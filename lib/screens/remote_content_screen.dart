import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image_picker/image_picker.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';

enum _ContentSort { manual, newest, oldest, titleAsc, titleDesc }

class RemoteContentScreen extends StatefulWidget {
  final String section;
  final String title;
  final String emptyText;
  final IconData icon;
  final bool archiveStyle;
  final bool individualImages;

  const RemoteContentScreen({
    required this.section,
    required this.title,
    required this.emptyText,
    required this.icon,
    this.archiveStyle = false,
    this.individualImages = false,
    super.key,
  });

  const RemoteContentScreen.archiveStyle({
    required this.section,
    required this.title,
    required this.emptyText,
    required this.icon,
    this.archiveStyle = true,
    this.individualImages = false,
    super.key,
  });

  @override
  State<RemoteContentScreen> createState() => _RemoteContentScreenState();
}

class _RemoteContentScreenState extends State<RemoteContentScreen> {
  _ContentSort sort = _ContentSort.manual;

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

  Future<void> _openDocument(
    BuildContext context,
    AppStore store,
    ContentItem item,
  ) async {
    if (item.documentUrl.isEmpty) return;
    try {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('PDF wird geöffnet …')),
      );
      final bytes = await store.api.downloadDocument(item.documentUrl);
      final directory = await getTemporaryDirectory();
      final safeName = item.documentName.trim().isEmpty
          ? 'flapamamaku-dokument.pdf'
          : item.documentName.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
      final file = File('${directory.path}/$safeName');
      await file.writeAsBytes(bytes, flush: true);
      final result = await OpenFilex.open(file.path, type: 'application/pdf');
      if (result.type != ResultType.done && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('PDF konnte nicht geöffnet werden: ${result.message}')),
        );
      }
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('PDF konnte nicht geladen werden: $error')),
      );
    }
  }

  Future<void> _votePoll(
    BuildContext context,
    AppStore store,
    ContentItem item,
    int optionIndex,
  ) async {
    if (item.id == null) return;
    try {
      await store.api.votePoll(item.id!, optionIndex);
      await store.refreshFromServer();
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Deine Stimme wurde gespeichert.')),
      );
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Abstimmung fehlgeschlagen: $error')),
      );
    }
  }

  Future<void> _deleteItem(
    BuildContext context,
    AppStore store,
    ContentItem item,
  ) async {
    if (item.id == null && item.snapshotId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(item.isSnapshot ? 'Snapshot löschen?' : 'Eintrag löschen?'),
        content: Text(
          item.isSnapshot
              ? '„${item.title}“ wird aus der Galerie gelöscht.'
              : '„${item.title}“ wird inklusive Bilder gelöscht.',
        ),
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
      case _ContentSort.manual:
        items.sort((a, b) {
          final byOrder = a.sortOrder.compareTo(b.sortOrder);
          if (byOrder != 0) return byOrder;
          return (a.id ?? 0).compareTo(b.id ?? 0);
        });
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
      case _ContentSort.manual:
        return 'Docker-Reihenfolge';
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

  List<ContentItem> _individualItems(List<ContentItem> items) {
    final result = <ContentItem>[];
    for (final item in items) {
      final urls = _images(item);
      if (urls.isEmpty) {
        result.add(item);
        continue;
      }
      for (final url in urls) {
        result.add(
          ContentItem(
            id: item.id,
            section: item.section,
            title: item.title,
            text: item.text,
            linkUrl: item.linkUrl,
            imageUrl: url,
            imageUrls: [url],
            createdAt: item.createdAt,
            sortOrder: item.sortOrder,
            snapshotId: item.snapshotId,
            isSnapshot: item.isSnapshot,
            canDelete: item.canDelete,
            expiresAt: item.expiresAt,
          ),
        );
      }
    }
    return result;
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

  Future<void> _captureSnapshot(BuildContext context, AppStore store) async {
    try {
      final photo = await ImagePicker().pickImage(
        source: ImageSource.camera,
        imageQuality: 82,
        maxWidth: 1600,
      );
      if (photo == null || !context.mounted) return;

      var bytes = await photo.readAsBytes();

      const maxBytes = 2 * 1024 * 1024;
      if (bytes.length > maxBytes) {
        for (final quality in [75, 68, 60, 52, 45]) {
          bytes = await FlutterImageCompress.compressWithList(
            bytes,
            minWidth: 1280,
            quality: quality,
            format: CompressFormat.jpeg,
          );
          if (bytes.length <= maxBytes) break;
        }
      }

      if (bytes.length > maxBytes) {
        bytes = await FlutterImageCompress.compressWithList(
          bytes,
          minWidth: 1024,
          quality: 42,
          format: CompressFormat.jpeg,
        );
      }

      if (bytes.length > maxBytes) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Foto konnte nicht unter 2 MB verkleinert werden. Bitte nochmals aufnehmen.',
            ),
          ),
        );
        return;
      }

      if (!context.mounted) return;

      int selectedDays = 14;
      final expiresDays = await showDialog<int>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, setDialogState) => AlertDialog(
            title: const Text('Snapshot hochladen'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(
                    bytes,
                    height: 220,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<int>(
                  initialValue: selectedDays,
                  decoration: const InputDecoration(
                    labelText: 'Automatisch löschen nach',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 7, child: Text('7 Tagen')),
                    DropdownMenuItem(value: 14, child: Text('14 Tagen')),
                    DropdownMenuItem(value: 30, child: Text('30 Tagen')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setDialogState(() => selectedDays = value);
                    }
                  },
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: const Text('Abbrechen'),
              ),
              FilledButton.icon(
                onPressed: () => Navigator.of(dialogContext).pop(selectedDays),
                icon: const Icon(Icons.cloud_upload_outlined),
                label: const Text('Hochladen'),
              ),
            ],
          ),
        ),
      );

      if (expiresDays == null || !context.mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Snapshot wird hochgeladen …')),
      );
      await store.uploadGallerySnapshot(
        bytes: bytes,
        filename: 'snapshot.jpg',
        expiresDays: expiresDays,
      );
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Snapshot gespeichert – automatische Löschung nach $expiresDays Tagen.',
          ),
        ),
      );
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Snapshot konnte nicht gespeichert werden: $error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final sourceItems = store.contentFor(widget.section);
    final sortedItems = _sortedItems(sourceItems);
    final items = widget.individualImages
        ? _individualItems(sortedItems)
        : sortedItems;

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
      bottomNavigationBar: widget.section == 'gallery' && store.canGalleryUpload
          ? SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(54),
                    backgroundColor: FlapBrand.burgundy,
                    foregroundColor: Colors.white,
                    textStyle: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  onPressed: () => _captureSnapshot(context, store),
                  icon: const Icon(Icons.camera_alt_rounded),
                  label: const Text('Foto aufnehmen'),
                ),
              ),
            )
          : null,
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: items.isEmpty
            ? _EmptyState(icon: widget.icon, text: widget.emptyText)
            : widget.section == 'links'
                ? _LinkList(
                    items: items,
                    headers: store.api.authHeaders,
                    onOpen: (item) => _openLink(context, item.linkUrl),
                    onDelete: store.canEditContentSection(widget.section)
                        ? (item) => _deleteItem(context, store, item)
                        : null,
                  )
                : widget.section == 'documents'
                ? _DocumentList(
                    items: items,
                    onOpen: (item) => _openDocument(context, store, item),
                  )
                : widget.section == 'polls'
                ? _PollList(
                    items: items,
                    onVote: (item, optionIndex) =>
                        _votePoll(context, store, item, optionIndex),
                  )
                : widget.archiveStyle
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
                        onDelete: item.isSnapshot
                            ? (item.canDelete
                                ? () => _deleteItem(context, store, item)
                                : null)
                            : store.canEditContentSection(widget.section)
                                ? () => _deleteItem(context, store, item)
                                : null,
                      );
                    },
                  ),
      ),
    );
  }
}

class _LinkList extends StatelessWidget {
  final List<ContentItem> items;
  final Map<String, String> headers;
  final ValueChanged<ContentItem> onOpen;
  final ValueChanged<ContentItem>? onDelete;

  const _LinkList({
    required this.items,
    required this.headers,
    required this.onOpen,
    this.onDelete,
  });

  String _uploadedLogo(ContentItem item) {
    for (final value in item.imageUrls) {
      if (value.trim().isNotEmpty) return value.trim();
    }
    return item.imageUrl.trim();
  }

  String _favicon(ContentItem item) {
    final raw = item.linkUrl.trim();
    if (raw.isEmpty) return '';
    final normalized = raw.startsWith('http://') || raw.startsWith('https://')
        ? raw
        : 'https://$raw';
    final uri = Uri.tryParse(normalized);
    if (uri == null || uri.host.isEmpty) return '';
    return uri.replace(path: '/favicon.ico', query: null, fragment: null).toString();
  }

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) {
        final item = items[index];
        final uploadedLogo = _uploadedLogo(item);
        final favicon = _favicon(item);
        final logo = uploadedLogo.isNotEmpty ? uploadedLogo : favicon;
        final canOpen = item.linkUrl.trim().isNotEmpty;

        return Material(
          color: const Color(0xFF191B1E),
          borderRadius: BorderRadius.circular(18),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: canOpen ? () => onOpen(item) : null,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 8, 12),
              child: Row(
                children: [
                  Container(
                    width: 66,
                    height: 66,
                    decoration: BoxDecoration(
                      color: logo.isEmpty ? FlapBrand.burgundy : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: logo.isEmpty
                        ? const Icon(
                            Icons.link_rounded,
                            color: Colors.white,
                            size: 31,
                          )
                        : Padding(
                            padding: const EdgeInsets.all(6),
                            child: Image.network(
                              logo,
                              headers: uploadedLogo.isNotEmpty ? headers : null,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Icon(
                                Icons.link_rounded,
                                color: FlapBrand.burgundy,
                                size: 31,
                              ),
                            ),
                          ),
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
                            fontSize: 17,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        if (item.text.trim().isNotEmpty) ...[
                          const SizedBox(height: 3),
                          Text(
                            item.text.trim(),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white60),
                          ),
                        ],
                        if (canOpen) ...[
                          const SizedBox(height: 5),
                          Text(
                            item.linkUrl,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: FlapBrand.gold,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (canOpen)
                    const Icon(
                      Icons.open_in_new_rounded,
                      color: FlapBrand.gold,
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
          ),
        );
      },
    );
  }
}

class _DocumentList extends StatelessWidget {
  final List<ContentItem> items;
  final ValueChanged<ContentItem> onOpen;

  const _DocumentList({required this.items, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) {
        final item = items[index];
        final hasPdf = item.documentUrl.trim().isNotEmpty;
        return Material(
          color: const Color(0xFF191B1E),
          borderRadius: BorderRadius.circular(18),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: hasPdf ? () => onOpen(item) : null,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 54,
                    height: 54,
                    decoration: BoxDecoration(
                      color: FlapBrand.burgundy,
                      borderRadius: BorderRadius.circular(15),
                    ),
                    child: const Icon(
                      Icons.picture_as_pdf_rounded,
                      color: Colors.white,
                      size: 30,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        if (item.text.trim().isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            item.text.trim(),
                            style: const TextStyle(color: Colors.white60),
                          ),
                        ],
                        const SizedBox(height: 5),
                        Text(
                          hasPdf
                              ? (item.documentName.isEmpty
                                  ? 'PDF öffnen'
                                  : item.documentName)
                              : 'Noch keine PDF hinterlegt',
                          style: TextStyle(
                            color: hasPdf ? FlapBrand.gold : Colors.white38,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (hasPdf)
                    const Icon(Icons.open_in_new_rounded, color: FlapBrand.gold),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PollList extends StatelessWidget {
  final List<ContentItem> items;
  final void Function(ContentItem item, int optionIndex) onVote;

  const _PollList({required this.items, required this.onVote});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 14),
      itemBuilder: (_, index) {
        final item = items[index];
        final total = item.pollTotalVotes;
        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF191B1E),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0x18FFFFFF)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.how_to_vote_rounded, color: FlapBrand.gold),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      item.title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
              if (item.text.trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(item.text.trim(), style: const TextStyle(color: Colors.white70)),
              ],
              const SizedBox(height: 14),
              ...List.generate(item.pollOptions.length, (optionIndex) {
                final count = optionIndex < item.pollCounts.length
                    ? item.pollCounts[optionIndex]
                    : 0;
                final percent = total == 0 ? 0.0 : count / total;
                final selected = item.pollMyVote == optionIndex;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () => onVote(item, optionIndex),
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: selected
                            ? FlapBrand.burgundy.withValues(alpha: 0.35)
                            : const Color(0xFF24272B),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: selected ? FlapBrand.gold : const Color(0x18FFFFFF),
                        ),
                      ),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Icon(
                                selected
                                    ? Icons.radio_button_checked
                                    : Icons.radio_button_off,
                                color: selected ? FlapBrand.gold : Colors.white54,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  item.pollOptions[optionIndex],
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                              Text(
                                '$count',
                                style: const TextStyle(
                                  color: FlapBrand.gold,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: percent,
                              minHeight: 6,
                              backgroundColor: Colors.white12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
              Text(
                total == 1 ? '1 Stimme' : '$total Stimmen',
                style: const TextStyle(
                  color: Colors.white54,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF24272B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0x18FFFFFF)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Teilnehmende ($total)',
                      style: const TextStyle(
                        color: FlapBrand.gold,
                        fontWeight: FontWeight.w900,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 10),
                    if (item.pollVoters.isEmpty)
                      const Text(
                        'Noch niemand hat abgestimmt.',
                        style: TextStyle(color: Colors.white54),
                      )
                    else
                      ...item.pollVoters.map((voter) {
                        final answer =
                            voter.optionIndex >= 0 &&
                                    voter.optionIndex < item.pollOptions.length
                                ? item.pollOptions[voter.optionIndex]
                                : 'Unbekannte Antwort';
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(
                                Icons.person_outline_rounded,
                                color: Colors.white54,
                                size: 20,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  voter.name,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Flexible(
                                child: Text(
                                  answer,
                                  textAlign: TextAlign.right,
                                  style: const TextStyle(
                                    color: FlapBrand.gold,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                  ],
                ),
              ),
            ],
          ),
        );
      },
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
              behavior: HitTestBehavior.opaque,
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
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: urls.isEmpty ? null : () => onOpen(item),
              child: Padding(
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
  final TransformationController _transformation = TransformationController();
  late int index;
  bool sharing = false;

  @override
  void initState() {
    super.initState();
    index = widget.initialIndex;
  }

  @override
  void dispose() {
    _transformation.dispose();
    super.dispose();
  }

  void _showImage(int nextIndex) {
    if (nextIndex < 0 || nextIndex >= widget.urls.length) return;
    _transformation.value = Matrix4.identity();
    setState(() => index = nextIndex);
  }

  void _changeScale(double change) {
    final current = _transformation.value.getMaxScaleOnAxis();
    final target = (current + change).clamp(1.0, 5.0).toDouble();
    _transformation.value = Matrix4.diagonal3Values(target, target, 1);
  }

  void _resetScale() {
    _transformation.value = Matrix4.identity();
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
      final directory = await getTemporaryDirectory();
      final file = File('${directory.path}/$filename');
      await file.writeAsBytes(downloaded.bytes, flush: true);
      await SharePlus.instance.share(
        ShareParams(
          title: 'Bild speichern oder teilen',
          files: [XFile(file.path, mimeType: downloaded.mimeType)],
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
          Positioned.fill(
            child: InteractiveViewer(
              key: ValueKey(widget.urls[index]),
              transformationController: _transformation,
              minScale: 1,
              maxScale: 5,
              panEnabled: true,
              scaleEnabled: true,
              boundaryMargin: const EdgeInsets.all(80),
              child: Center(
                child: Image.network(
                  widget.urls[index],
                  headers: headers,
                  width: double.infinity,
                  fit: BoxFit.contain,
                  filterQuality: FilterQuality.medium,
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
          Positioned(
            left: 12,
            right: 12,
            bottom: 18,
            child: SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xD9111315),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: const Color(0x33FFFFFF)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      tooltip: 'Vorheriges Bild',
                      onPressed: index == 0 ? null : () => _showImage(index - 1),
                      color: Colors.white,
                      disabledColor: Colors.white24,
                      icon: const Icon(Icons.chevron_left_rounded),
                    ),
                    IconButton(
                      tooltip: 'Verkleinern',
                      onPressed: () => _changeScale(-0.75),
                      color: Colors.white,
                      icon: const Icon(Icons.zoom_out_rounded),
                    ),
                    IconButton(
                      tooltip: 'Originalgröße',
                      onPressed: _resetScale,
                      color: FlapBrand.gold,
                      icon: const Icon(Icons.center_focus_strong_rounded),
                    ),
                    IconButton(
                      tooltip: 'Vergrößern',
                      onPressed: () => _changeScale(0.75),
                      color: Colors.white,
                      icon: const Icon(Icons.zoom_in_rounded),
                    ),
                    IconButton(
                      tooltip: 'Speichern / Teilen',
                      onPressed: sharing ? null : _shareCurrent,
                      color: FlapBrand.gold,
                      icon: sharing
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.ios_share_rounded),
                    ),
                    IconButton(
                      tooltip: 'Nächstes Bild',
                      onPressed: index == widget.urls.length - 1
                          ? null
                          : () => _showImage(index + 1),
                      color: Colors.white,
                      disabledColor: Colors.white24,
                      icon: const Icon(Icons.chevron_right_rounded),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
