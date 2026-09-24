import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';

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

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final images = _images(store);

    if (_page >= images.length && images.isNotEmpty) {
      _page = 0;
    }

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Sujet nächstes Jahr'),
        actions: [
          IconButton(
            tooltip: 'Aktualisieren',
            onPressed: store.isSyncing
                ? null
                : () async {
                    await store.refreshFromServer();
                    if (mounted) setState(() {});
                  },
            icon: store.isSyncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
        ],
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
          : Stack(
              children: [
                PageView.builder(
                  controller: _controller,
                  itemCount: images.length,
                  onPageChanged: (value) => setState(() => _page = value),
                  itemBuilder: (_, index) {
                    final image = images[index];
                    return Column(
                      children: [
                        Expanded(
                          child: InteractiveViewer(
                            minScale: 1,
                            maxScale: 4,
                            child: Center(
                              child: Image.network(
                                image.url,
                                headers: store.api.authHeaders,
                                fit: BoxFit.contain,
                                width: double.infinity,
                                errorBuilder: (_, __, ___) => const Center(
                                  child: Text(
                                    'Bild konnte nicht geladen werden.',
                                    style: TextStyle(color: Colors.white),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        if (image.item.title.isNotEmpty ||
                            image.item.text.isNotEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
                            color: Colors.black87,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (image.item.title.isNotEmpty)
                                  Text(
                                    image.item.title,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 20,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                if (image.item.text.isNotEmpty) ...[
                                  const SizedBox(height: 6),
                                  Text(
                                    image.item.text,
                                    style: const TextStyle(
                                      color: Colors.white70,
                                      fontSize: 15,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                      ],
                    );
                  },
                ),
                if (images.length > 1)
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 10,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        images.length,
                        (index) => Container(
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          width: index == _page ? 20 : 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color:
                                index == _page ? Colors.white : Colors.white54,
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
