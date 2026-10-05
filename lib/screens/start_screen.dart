import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../widgets/offline_network_image.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import 'flap_image_viewer_screen.dart';
import 'members_screen.dart';
import 'more_screen.dart';
import 'remote_content_screen.dart';
import 'content_detail_screens.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  ContentItem? _latestContent(AppStore store, String section) {
    final items = List<ContentItem>.from(store.contentFor(section));
    if (items.isEmpty) return null;
    items.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return items.first;
  }

  String _contentImage(ContentItem? item) {
    if (item == null) return '';
    if (item.imageUrls.isNotEmpty) {
      for (final url in item.imageUrls) {
        if (url.trim().isNotEmpty) return url.trim();
      }
    }
    return item.imageUrl.trim();
  }

  Widget _heroPlaceholder(BuildContext context, AppStore store) {
    if (store.appLogoUrl.trim().isNotEmpty) {
      return ColoredBox(
        color: const Color(0xFF061018),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: OfflineNetworkImage(
            store.appLogoUrl,
            fit: BoxFit.contain,
            headers: const {},
            errorBuilder: (_, __, ___) => _neutralHero(store),
          ),
        ),
      );
    }
    return _neutralHero(store);
  }

  Widget _neutralHero(AppStore store) {
    return ColoredBox(
      color: const Color(0xFF101317),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.image_outlined,
                size: 66,
                color: store.themeColor.withValues(alpha: 0.85),
              ),
              const SizedBox(height: 16),
              Text(
                store.appName,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Noch kein Hauptbild hinterlegt.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white60),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final hero = _latestContent(store, 'hero');
    final heroImage = _contentImage(hero);
    final heroTitle = hero == null || hero.title.trim().isEmpty
        ? store.appName
        : hero.title.trim();
    final latestNews = store.news.take(3).toList();
    final sujetItems = List<ContentItem>.from(store.contentFor('sujet'))
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: EdgeInsets.zero,
          children: [
            Container(
              color: const Color(0xFF061018),
              padding: const EdgeInsets.fromLTRB(14, 46, 14, 12),
              child: Row(
                children: [
                  IconButton(
                    tooltip: 'Mehr',
                    color: Colors.white,
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const MoreScreen()),
                    ),
                    icon: const Icon(Icons.menu_rounded, size: 28),
                  ),
                  Expanded(
                    child: Text(
                      store.appName,
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: store.themeColor,
                        fontSize: 25,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.1,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Mitglieder',
                    color: Colors.white,
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const MembersScreen()),
                    ),
                    icon: const Icon(Icons.person_outline_rounded, size: 28),
                  ),
                ],
              ),
            ),
            GestureDetector(
              onTap: heroImage.isEmpty
                  ? null
                  : () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => FlapImageViewerScreen(
                            title: heroTitle,
                            imageUrl: heroImage,
                          ),
                        ),
                      ),
              child: Stack(
                children: [
                  SizedBox(
                    width: double.infinity,
                    height: 480,
                    child: heroImage.isNotEmpty
                        ? OfflineNetworkImage(
                            heroImage,
                            headers: store.api.authHeaders,
                            fit: BoxFit.contain,
                            alignment: Alignment.center,
                            errorBuilder: (_, __, ___) =>
                                _heroPlaceholder(context, store),
                          )
                        : _heroPlaceholder(context, store),
                  ),
                  if (heroImage.isNotEmpty)
                    const Positioned(
                      right: 14,
                      bottom: 14,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Color(0xB8000000),
                          shape: BoxShape.circle,
                        ),
                        child: Padding(
                          padding: EdgeInsets.all(8),
                          child: Icon(
                            Icons.zoom_in_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            if (store.showSujet)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.auto_awesome_rounded,
                          color: FlapBrand.gold,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            store.labelSujet,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: () => Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => RemoteContentScreen.archiveStyle(
                                section: 'sujet',
                                title: store.labelSujet,
                                emptyText: 'Noch keine Inhalte hinterlegt.',
                                icon: Icons.auto_awesome_rounded,
                              ),
                            ),
                          ),
                          child: const Text('Alle'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (sujetItems.isEmpty)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: const Color(0xFF191B1E),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0x18FFFFFF)),
                        ),
                        child: const Text(
                          'Noch keine Sujet-Bilder hinterlegt.',
                          style: TextStyle(color: Colors.white60),
                        ),
                      )
                    else
                      _SujetPreviewSlider(
                        items: sujetItems,
                        headers: store.api.authHeaders,
                        title: store.labelSujet,
                        onOpenAll: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => RemoteContentScreen.archiveStyle(
                              section: 'sujet',
                              title: store.labelSujet,
                              emptyText: 'Noch keine Inhalte hinterlegt.',
                              icon: Icons.auto_awesome_rounded,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.article_rounded, color: FlapBrand.gold),
                      SizedBox(width: 8),
                      Text(
                        'News',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (latestNews.isEmpty)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: const Color(0xFF191B1E),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0x18FFFFFF)),
                      ),
                      child: const Text(
                        'Noch keine News vorhanden.',
                        style: TextStyle(color: Colors.white60),
                      ),
                    )
                  else
                    ...latestNews.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Material(
                          color: const Color(0xFF191B1E),
                          borderRadius: BorderRadius.circular(16),
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () => Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => NewsDetailScreen(item: item),
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (item.imageUrl.isNotEmpty ||
                                    item.imageAsset.isNotEmpty)
                                  SizedBox(
                                    width: 108,
                                    height: 108,
                                    child: item.imageUrl.isNotEmpty
                                        ? OfflineNetworkImage(
                                            item.imageUrl,
                                            headers: store.api.authHeaders,
                                            fit: BoxFit.contain,
                                            errorBuilder: (_, __, ___) =>
                                                const ColoredBox(
                                              color: Color(0xFF24272B),
                                            ),
                                          )
                                        : Image.asset(
                                            item.imageAsset,
                                            fit: BoxFit.contain,
                                          ),
                                  ),
                                Expanded(
                                  child: Padding(
                                    padding: const EdgeInsets.fromLTRB(
                                      14,
                                      12,
                                      10,
                                      12,
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.date,
                                          style: const TextStyle(
                                            color: FlapBrand.gold,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          item.title,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 17,
                                            fontWeight: FontWeight.w900,
                                          ),
                                        ),
                                        if (item.text.trim().isNotEmpty) ...[
                                          const SizedBox(height: 5),
                                          Text(
                                            item.text,
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              color: Colors.white60,
                                              height: 1.25,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),
                                const Padding(
                                  padding: EdgeInsets.only(top: 39, right: 8),
                                  child: Icon(
                                    Icons.chevron_right_rounded,
                                    color: Colors.white38,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SujetPreviewEntry {
  final String imageUrl;
  final String title;

  const _SujetPreviewEntry({
    required this.imageUrl,
    required this.title,
  });
}

class _SujetPreviewSlider extends StatefulWidget {
  final List<ContentItem> items;
  final Map<String, String> headers;
  final String title;
  final VoidCallback onOpenAll;

  const _SujetPreviewSlider({
    required this.items,
    required this.headers,
    required this.title,
    required this.onOpenAll,
  });

  @override
  State<_SujetPreviewSlider> createState() => _SujetPreviewSliderState();
}

class _SujetPreviewSliderState extends State<_SujetPreviewSlider> {
  late final PageController _controller;
  int _page = 0;

  List<_SujetPreviewEntry> get _entries {
    final result = <_SujetPreviewEntry>[];
    for (final item in widget.items) {
      final urls = item.imageUrls.isNotEmpty
          ? item.imageUrls
          : item.imageUrl.trim().isNotEmpty
              ? <String>[item.imageUrl]
              : const <String>[];
      for (final rawUrl in urls) {
        final url = rawUrl.trim();
        if (url.isEmpty) continue;
        result.add(
          _SujetPreviewEntry(
            imageUrl: url,
            title: item.title.trim().isEmpty ? widget.title : item.title.trim(),
          ),
        );
      }
    }
    return result;
  }

  @override
  void initState() {
    super.initState();
    _controller = PageController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final entries = _entries;
    if (entries.isEmpty) {
      return Material(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: widget.onOpenAll,
          child: const Padding(
            padding: EdgeInsets.all(18),
            child: Text(
              'Noch keine Sujet-Bilder hinterlegt.',
              style: TextStyle(color: Colors.white60),
            ),
          ),
        ),
      );
    }

    if (_page >= entries.length) {
      _page = 0;
    }

    return Material(
      color: const Color(0xFF191B1E),
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: widget.onOpenAll,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: 16 / 10,
              child: Stack(
                alignment: Alignment.bottomCenter,
                children: [
                  PageView.builder(
                    controller: _controller,
                    itemCount: entries.length,
                    onPageChanged: (value) => setState(() => _page = value),
                    itemBuilder: (_, index) => OfflineNetworkImage(
                      entries[index].imageUrl,
                      headers: widget.headers,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const ColoredBox(
                        color: Color(0xFF24272B),
                        child: Center(
                          child: Icon(
                            Icons.broken_image_outlined,
                            color: Colors.white38,
                            size: 48,
                          ),
                        ),
                      ),
                    ),
                  ),
                  if (entries.length > 1)
                    Positioned(
                      bottom: 10,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: const Color(0x88000000),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 6,
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: List.generate(
                              entries.length,
                              (index) => AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                margin:
                                    const EdgeInsets.symmetric(horizontal: 3),
                                width: index == _page ? 18 : 7,
                                height: 7,
                                decoration: BoxDecoration(
                                  color: index == _page
                                      ? Colors.white
                                      : Colors.white54,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      entries[_page].title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const Icon(
                    Icons.chevron_right_rounded,
                    color: Colors.white54,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
