import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import '../widgets/section_title.dart';
import 'year_motto_screen.dart';
import 'remote_content_screen.dart';
import 'content_detail_screens.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

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

  List<String> _sujetImages(AppStore store) {
    final images = <String>[];
    for (final item in store.contentFor('sujet')) {
      if (item.imageUrls.isNotEmpty) {
        images.addAll(item.imageUrls.where((url) => url.trim().isNotEmpty));
      } else if (item.imageUrl.trim().isNotEmpty) {
        images.add(item.imageUrl);
      }
    }
    return images;
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final latestNewsImage = store.news.isEmpty
        ? null
        : _newsImage(store.news.first, store.api.authHeaders);
    final sujetImages = _sujetImages(store);

    return RefreshIndicator(
      onRefresh: store.refreshFromServer,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverAppBar(
            expandedHeight: 285,
            pinned: true,
            backgroundColor: FlapBrand.charcoal,
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  Image.asset(
                    'assets/images/hero_fireworks.jpg',
                    width: double.infinity,
                    height: double.infinity,
                    fit: BoxFit.cover,
                  ),
                  const DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [Color(0x22000000), Color(0xDD000000)],
                      ),
                    ),
                  ),
                  const Positioned(
                    left: 20,
                    right: 20,
                    bottom: 24,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'DIE SCHWEINE ROCKER',
                          style: TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.4,
                          ),
                        ),
                        SizedBox(height: 6),
                        Text(
                          'der Stadt Luzern',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 30,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
            sliver: SliverList.list(
              children: [
                InkWell(
                  borderRadius: BorderRadius.circular(22),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                  ),
                  child: sujetImages.isEmpty
                      ? Card(
                          margin: EdgeInsets.zero,
                          child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Row(
                              children: [
                                Icon(
                                  Icons.auto_awesome_outlined,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                                const SizedBox(width: 12),
                                const Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Sujet nächstes Jahr',
                                        style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                      SizedBox(height: 4),
                                      Text(
                                        'Noch keine Sujet-Bilder hinterlegt.',
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right),
                              ],
                            ),
                          ),
                        )
                      : SujetSlider(
                          images: sujetImages,
                          headers: store.api.authHeaders,
                        ),
                ),
                const SizedBox(height: 26),
                const SectionTitle('Aktuelle News', action: 'Alle'),
                const SizedBox(height: 8),
                if (store.news.isNotEmpty)
                  Card(
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => NewsDetailScreen(
                            item: store.news.first,
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (latestNewsImage != null) latestNewsImage,
                          Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  store.news.first.date,
                                  style: TextStyle(
                                    color:
                                        Theme.of(context).colorScheme.primary,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  store.news.first.title,
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  store.news.first.text,
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  const Card(
                    child: ListTile(
                      title: Text('Keine News vorhanden'),
                    ),
                  ),
                const SizedBox(height: 20),
                const SectionTitle('Nächste Termine', action: 'Alle'),
                const SizedBox(height: 8),
                ...store.events.take(2).map(
                  (e) => Card(
                    child: ListTile(
                      leading: SizedBox(
                        width: 48,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              e.day,
                              style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(e.month),
                          ],
                        ),
                      ),
                      title: Text(e.title),
                      subtitle: Text('${e.location} · ${e.time}'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => EventDetailScreen(event: e),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Card(
                  child: ListTile(
                    leading: const CircleAvatar(
                      child: Icon(Icons.photo_library_outlined),
                    ),
                    title: const Text(
                      'Vergangene Sujet',
                      style: TextStyle(fontWeight: FontWeight.w800),
                    ),
                    subtitle: const Text(
                      'Frühere Sujets, Mottos und Erinnerungen',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const RemoteContentScreen(
                          section: 'archive',
                          title: 'Vergangene Sujet',
                          emptyText:
                              'Noch keine vergangenen Sujets hinterlegt.',
                          icon: Icons.history,
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
    );
  }
}

class SujetSlider extends StatefulWidget {
  final List<String> images;
  final Map<String, String> headers;

  const SujetSlider({
    required this.images,
    required this.headers,
    super.key,
  });

  @override
  State<SujetSlider> createState() => _SujetSliderState();
}

class _SujetSliderState extends State<SujetSlider> {
  late final PageController _controller;
  int _page = 0;

  @override
  void initState() {
    super.initState();
    _controller = PageController();
  }

  @override
  void didUpdateWidget(covariant SujetSlider oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_page >= widget.images.length) {
      _page = 0;
      if (_controller.hasClients) {
        _controller.jumpToPage(0);
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      margin: EdgeInsets.zero,
      child: Stack(
        alignment: Alignment.bottomCenter,
        children: [
          AspectRatio(
            aspectRatio: 16 / 10,
            child: PageView.builder(
              controller: _controller,
              itemCount: widget.images.length,
              onPageChanged: (value) => setState(() => _page = value),
              itemBuilder: (_, index) => Image.network(
                widget.images[index],
                headers: widget.headers,
                fit: BoxFit.cover,
                width: double.infinity,
                errorBuilder: (_, __, ___) => Container(
                  alignment: Alignment.center,
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.broken_image_outlined, size: 48),
                ),
              ),
            ),
          ),
          if (widget.images.length > 1)
            Positioned(
              bottom: 10,
              child: Row(
                children: List.generate(
                  widget.images.length,
                  (index) => AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    width: index == _page ? 18 : 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color:
                          index == _page ? Colors.white : Colors.white60,
                      borderRadius: BorderRadius.circular(12),
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
