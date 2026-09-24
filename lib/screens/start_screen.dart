import 'dart:async';
import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../widgets/section_title.dart';
import 'year_motto_screen.dart';
import 'archive_screen.dart';
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

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final latestNewsImage = store.news.isEmpty
        ? null
        : _newsImage(store.news.first, store.api.authHeaders);

    return CustomScrollView(
      slivers: [
        SliverAppBar(
          expandedHeight: 285,
          pinned: true,
          backgroundColor: const Color(0xFF8A101B),
          flexibleSpace: FlexibleSpaceBar(
            background: Stack(
              fit: StackFit.expand,
              children: [
                Image.asset(
                  'assets/FLAPAMAMAKU App-Icon.png',
                  width: double.infinity,
                  height: double.infinity,
                  fit: BoxFit.cover,
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
                borderRadius: BorderRadius.circular(18),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                ),
                child: const SujetSlider(),
              ),
              const SizedBox(height: 22),
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
                                  color: Theme.of(context).colorScheme.primary,
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
                    'Archiv',
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: const Text(
                    'Frühere Sujets, Mottos und Erinnerungen',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ArchiveScreen()),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class SujetSlider extends StatefulWidget {
  const SujetSlider({super.key});

  @override
  State<SujetSlider> createState() => _SujetSliderState();
}

class _SujetSliderState extends State<SujetSlider> {
  static const _images = [
    'assets/images/year_motto_pig_rockers.jpg',
    'assets/images/archive_top_hats_night.jpg',
    'assets/images/archive_top_hats_barrel.jpg',
    'assets/images/archive_vikings_bar.jpg',
  ];

  final _controller = PageController();
  Timer? _timer;
  int _page = 0;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!mounted || !_controller.hasClients) return;
      final next = (_page + 1) % _images.length;
      _controller.animateToPage(
        next,
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeInOut,
      );
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
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
              itemCount: _images.length,
              onPageChanged: (value) => setState(() => _page = value),
              itemBuilder: (_, index) => Image.asset(
                _images[index],
                fit: BoxFit.cover,
                width: double.infinity,
              ),
            ),
          ),
          Positioned(
            bottom: 10,
            child: Row(
              children: List.generate(
                _images.length,
                (index) => AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  width: index == _page ? 18 : 7,
                  height: 7,
                  decoration: BoxDecoration(
                    color: index == _page ? Colors.white : Colors.white60,
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
