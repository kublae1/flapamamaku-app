import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
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
    final sujetImages = _sujetImages(store);
    final latest = store.news.isEmpty ? null : store.news.first;
    final latestImage =
        latest == null ? null : _newsImage(latest, store.api.authHeaders);

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Stack(
                children: [
                  SizedBox(
                    height: 330,
                    width: double.infinity,
                    child: Image.asset(
                      'assets/images/hero_fireworks.jpg',
                      fit: BoxFit.cover,
                    ),
                  ),
                  Container(
                    height: 330,
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Color(0x22000000),
                          Color(0x77000000),
                          FlapBrand.charcoal,
                        ],
                      ),
                    ),
                  ),
                  Positioned(
                    left: 18,
                    right: 18,
                    top: 52,
                    child: Row(
                      children: [
                        Container(
                          width: 54,
                          height: 54,
                          padding: const EdgeInsets.all(5),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Image.asset('assets/FLAPAMAMAKU App-Icon.png'),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'FLAPAMAMAKU',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 1.3,
                                ),
                              ),
                              Text(
                                'Fasnachtsgruppe Luzern',
                                style: TextStyle(
                                  color: Colors.white70,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Positioned(
                    left: 18,
                    right: 18,
                    bottom: 34,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'DIE SCHWEINE ROCKER',
                          style: TextStyle(
                            color: FlapBrand.gold,
                            fontSize: 13,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 1.8,
                          ),
                        ),
                        SizedBox(height: 5),
                        Text(
                          'in der Bar',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 34,
                            height: 1,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
              sliver: SliverList.list(
                children: [
                  _BrandSectionTitle(
                    overline: 'JAHRESMOTTO',
                    title: 'Unser Sujet',
                    trailing: 'Ansehen',
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                    ),
                  ),
                  const SizedBox(height: 10),
                  GestureDetector(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(26),
                      child: Stack(
                        children: [
                          SizedBox(
                            height: 255,
                            width: double.infinity,
                            child: sujetImages.isNotEmpty
                                ? Image.network(
                                    sujetImages.first,
                                    headers: store.api.authHeaders,
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, __, ___) => Image.asset(
                                      'assets/images/year_motto_pig_rockers.jpg',
                                      fit: BoxFit.cover,
                                    ),
                                  )
                                : Image.asset(
                                    'assets/images/year_motto_pig_rockers.jpg',
                                    fit: BoxFit.cover,
                                  ),
                          ),
                          Container(
                            height: 255,
                            decoration: const BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [Colors.transparent, Color(0xDD000000)],
                              ),
                            ),
                          ),
                          const Positioned(
                            left: 18,
                            right: 18,
                            bottom: 17,
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Sujet nächstes Jahr',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 24,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ),
                                CircleAvatar(
                                  backgroundColor: FlapBrand.burgundy,
                                  foregroundColor: Colors.white,
                                  child: Icon(Icons.arrow_forward_rounded),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  const _BrandSectionTitle(
                    overline: 'AKTUELL',
                    title: 'News',
                  ),
                  const SizedBox(height: 10),
                  if (latest != null)
                    Card(
                      clipBehavior: Clip.antiAlias,
                      child: InkWell(
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => NewsDetailScreen(item: latest),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (latestImage != null) latestImage,
                            Container(
                              color: const Color(0xFF191B1E),
                              padding: const EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    latest.date.toUpperCase(),
                                    style: const TextStyle(
                                      color: FlapBrand.gold,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 1.2,
                                    ),
                                  ),
                                  const SizedBox(height: 7),
                                  Text(
                                    latest.title,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 23,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    latest.text,
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Colors.white70,
                                      height: 1.4,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    const _DarkInfoCard(text: 'Noch keine News vorhanden.'),
                  const SizedBox(height: 28),
                  const _BrandSectionTitle(
                    overline: 'KALENDER',
                    title: 'Nächste Termine',
                  ),
                  const SizedBox(height: 10),
                  ...store.events.take(2).map(
                    (event) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Card(
                        color: const Color(0xFF191B1E),
                        child: ListTile(
                          contentPadding:
                              const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          leading: Container(
                            width: 58,
                            height: 62,
                            decoration: BoxDecoration(
                              color: FlapBrand.burgundy,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  event.day,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 23,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                Text(
                                  event.month,
                                  style: const TextStyle(
                                    color: Colors.white70,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          title: Text(
                            event.title,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          subtitle: Text(
                            '${event.location} · ${event.time}',
                            style: const TextStyle(color: Colors.white60),
                          ),
                          trailing:
                              const Icon(Icons.chevron_right, color: Colors.white70),
                          onTap: () => Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => EventDetailScreen(event: event),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  _GalleryTile(
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
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandSectionTitle extends StatelessWidget {
  final String overline;
  final String title;
  final String? trailing;
  final VoidCallback? onTap;

  const _BrandSectionTitle({
    required this.overline,
    required this.title,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                overline,
                style: const TextStyle(
                  color: FlapBrand.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.6,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 25,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null)
          TextButton(
            onPressed: onTap,
            child: Text(
              trailing!,
              style: const TextStyle(color: FlapBrand.gold),
            ),
          ),
      ],
    );
  }
}

class _DarkInfoCard extends StatelessWidget {
  final String text;
  const _DarkInfoCard({required this.text});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFF191B1E),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Text(text, style: const TextStyle(color: Colors.white70)),
      ),
    );
  }
}

class _GalleryTile extends StatelessWidget {
  final VoidCallback onTap;
  const _GalleryTile({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(26),
      onTap: onTap,
      child: Container(
        height: 150,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(26),
          image: const DecorationImage(
            image: AssetImage('assets/images/archive_top_hats_night.jpg'),
            fit: BoxFit.cover,
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(26),
            gradient: const LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: [Color(0xEE000000), Color(0x33000000)],
            ),
          ),
          child: const Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ARCHIV & GALERIE',
                      style: TextStyle(
                        color: FlapBrand.gold,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.4,
                      ),
                    ),
                    SizedBox(height: 5),
                    Text(
                      'Vergangene Sujet',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 23,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
              ),
              CircleAvatar(
                backgroundColor: FlapBrand.burgundy,
                foregroundColor: Colors.white,
                child: Icon(Icons.photo_library_outlined),
              ),
            ],
          ),
        ),
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
