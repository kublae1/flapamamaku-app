import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';

class YearMottoScreen extends StatefulWidget {
  const YearMottoScreen({super.key});

  @override
  State<YearMottoScreen> createState() => _YearMottoScreenState();
}

class _MottoImage {
  final String url;
  final ContentItem item;

  const _MottoImage(this.url, this.item);
}

class _YearMottoScreenState extends State<YearMottoScreen> {
  final PageController _controller = PageController();
  int _page = 0;

  List<_MottoImage> _images(AppStore store) {
    final images = <_MottoImage>[];
    for (final item in store.contentFor('sujet')) {
      if (item.imageUrls.isNotEmpty) {
        for (final url in item.imageUrls) {
          if (url.trim().isNotEmpty) {
            images.add(_MottoImage(url, item));
          }
        }
      } else if (item.imageUrl.trim().isNotEmpty) {
        images.add(_MottoImage(item.imageUrl, item));
      }
    }
    return images;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _openFullscreen(
    BuildContext context,
    List<_MottoImage> images,
    int initialIndex,
  ) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _MottoFullscreenViewer(
          images: images,
          initialIndex: initialIndex,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final images = _images(store);

    if (_page >= images.length && images.isNotEmpty) {
      _page = 0;
    }

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Sujet nächstes Jahr',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: images.isEmpty
          ? RefreshIndicator(
              onRefresh: store.refreshFromServer,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 120),
                  Icon(
                    Icons.auto_awesome_outlined,
                    color: Colors.white70,
                    size: 64,
                  ),
                  SizedBox(height: 18),
                  Text(
                    'Noch kein Sujet fürs nächste Jahr hinterlegt.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white, fontSize: 18),
                  ),
                ],
              ),
            )
          : RefreshIndicator(
              onRefresh: store.refreshFromServer,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.zero,
                children: [
                  SizedBox(
                    height: 430,
                    child: PageView.builder(
                      controller: _controller,
                      itemCount: images.length,
                      onPageChanged: (value) => setState(() => _page = value),
                      itemBuilder: (_, index) {
                        final image = images[index];
                        return GestureDetector(
                          onTap: () => _openFullscreen(context, images, index),
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              Image.network(
                                image.url,
                                headers: store.api.authHeaders,
                                fit: BoxFit.cover,
                                width: double.infinity,
                                errorBuilder: (_, __, ___) => Container(
                                  color: const Color(0xFF24272B),
                                  alignment: Alignment.center,
                                  child: const Icon(
                                    Icons.broken_image_outlined,
                                    color: Colors.white54,
                                    size: 54,
                                  ),
                                ),
                              ),
                              const Positioned(
                                right: 14,
                                bottom: 14,
                                child: CircleAvatar(
                                  backgroundColor: Color(0xCC000000),
                                  foregroundColor: Colors.white,
                                  child: Icon(Icons.zoom_in_rounded),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  if (images.length > 1)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(
                          images.length,
                          (index) => AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            width: index == _page ? 22 : 7,
                            height: 7,
                            decoration: BoxDecoration(
                              color: index == _page
                                  ? FlapBrand.gold
                                  : Colors.white38,
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                        ),
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(22, 22, 22, 30),
                    child: Column(
                      children: [
                        if (images[_page].item.title.trim().isNotEmpty)
                          Text(
                            images[_page].item.title.trim(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        if (images[_page].item.text.trim().isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Text(
                            images[_page].item.text.trim(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 16,
                              height: 1.45,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _MottoFullscreenViewer extends StatefulWidget {
  final List<_MottoImage> images;
  final int initialIndex;

  const _MottoFullscreenViewer({
    required this.images,
    required this.initialIndex,
  });

  @override
  State<_MottoFullscreenViewer> createState() => _MottoFullscreenViewerState();
}

class _MottoFullscreenViewerState extends State<_MottoFullscreenViewer> {
  late final PageController _controller;
  late int index;

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

  @override
  Widget build(BuildContext context) {
    final headers = AppStoreScope.of(context).api.authHeaders;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Text(
          '${index + 1} / ${widget.images.length}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
      ),
      body: PageView.builder(
        controller: _controller,
        itemCount: widget.images.length,
        onPageChanged: (value) => setState(() => index = value),
        itemBuilder: (_, imageIndex) => InteractiveViewer(
          minScale: 1,
          maxScale: 5,
          child: Center(
            child: Image.network(
              widget.images[imageIndex].url,
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
    );
  }
}
