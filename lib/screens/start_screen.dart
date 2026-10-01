import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../widgets/offline_network_image.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import 'flap_image_viewer_screen.dart';
import 'members_screen.dart';
import 'more_screen.dart';
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

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final hero = _latestContent(store, 'hero');
    final heroImage = _contentImage(hero);
    final heroTitle = hero == null || hero.title.trim().isEmpty
        ? store.appName
        : hero.title.trim();
    const flapamamakuFallbackHero = 'assets/images/hero_wasserturm_saurocker.png';
    final isFlapamamaku = store.currentClubId == 1;
    final fallbackNetworkImage =
        !isFlapamamaku && store.appLogoUrl.isNotEmpty ? store.appLogoUrl : '';
    final fallbackAsset = isFlapamamaku ? flapamamakuFallbackHero : '';
    final latestNews = store.news.take(3).toList();

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
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => FlapImageViewerScreen(
                    title: heroTitle,
                    imageUrl: heroImage.isNotEmpty ? heroImage : fallbackNetworkImage,
                    imageAsset: fallbackAsset,
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
                            errorBuilder: (_, __, ___) => fallbackNetworkImage.isNotEmpty
                                ? OfflineNetworkImage(
                                    fallbackNetworkImage,
                                    fit: BoxFit.contain,
                                    alignment: Alignment.center,
                                    errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                                  )
                                : fallbackAsset.isNotEmpty
                                    ? Image.asset(
                                        fallbackAsset,
                                        fit: BoxFit.contain,
                                        alignment: Alignment.center,
                                      )
                                    : const SizedBox.shrink(),
                          )
                        : fallbackNetworkImage.isNotEmpty
                            ? OfflineNetworkImage(
                                fallbackNetworkImage,
                                fit: BoxFit.contain,
                                alignment: Alignment.center,
                                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                              )
                            : fallbackAsset.isNotEmpty
                                ? Image.asset(
                                    fallbackAsset,
                                    fit: BoxFit.contain,
                                    alignment: Alignment.center,
                                  )
                                : const SizedBox.shrink(),
                  ),
                  Positioned(
                    right: 14,
                    bottom: 14,
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: const BoxDecoration(
                        color: Color(0xB8000000),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.zoom_in_rounded,
                        color: Colors.white,
                        size: 22,
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
                                if (item.imageUrl.isNotEmpty || item.imageAsset.isNotEmpty)
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
                                    padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
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
