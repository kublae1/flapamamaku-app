import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import 'members_screen.dart';
import 'more_screen.dart';
import 'year_motto_screen.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  ContentItem? _latestContent(AppStore store, String section) {
    final items = List<ContentItem>.from(store.contentFor(section));
    if (items.isEmpty) return null;
    items.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return items.first;
  }

  String _heroImage(ContentItem? item) {
    if (item == null) return '';
    if (item.imageUrls.isNotEmpty) {
      for (final url in item.imageUrls) {
        if (url.trim().isNotEmpty) return url;
      }
    }
    return item.imageUrl.trim();
  }

  String _mottoYear(ContentItem? sujet) {
    final values = [
      sujet?.title ?? '',
      sujet?.text ?? '',
    ].join(' ');
    final match = RegExp(r'\b(20\d{2})\b').firstMatch(values);
    return match?.group(1) ?? DateTime.now().year.toString();
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final hero = _latestContent(store, 'hero');
    final sujet = _latestContent(store, 'sujet');
    final heroImage = _heroImage(hero);
    final heroTitle = hero != null && hero.title.trim().isNotEmpty
        ? hero.title.trim()
        : 'Die Schweine Rocker';
    final heroSubtitle = hero != null && hero.text.trim().isNotEmpty
        ? hero.text.trim()
        : 'in der Bar';
    final mottoYear = _mottoYear(sujet);

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
                  const Expanded(
                    child: Text(
                      'FLAPAMAMAKU',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFFE41F26),
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
            Stack(
              children: [
                SizedBox(
                  width: double.infinity,
                  height: 480,
                  child: heroImage.isNotEmpty
                      ? Image.network(
                          heroImage,
                          headers: store.api.authHeaders,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Image.asset(
                            'assets/images/hero_wasserturm_saurocker.jpg',
                            fit: BoxFit.cover,
                          ),
                        )
                      : Image.asset(
                          'assets/images/hero_wasserturm_saurocker.jpg',
                          fit: BoxFit.cover,
                        ),
                ),
                if (heroImage.isNotEmpty)
                  Positioned(
                    left: 22,
                    right: 22,
                    bottom: 24,
                    child: Container(
                      padding: const EdgeInsets.fromLTRB(16, 13, 16, 14),
                      decoration: BoxDecoration(
                        color: const Color(0xB8000000),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            heroTitle,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 25,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            heroSubtitle,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 23,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
              child: Material(
                color: const Color(0xFFE41F26),
                borderRadius: BorderRadius.circular(12),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(22, 14, 12, 14),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Jahresmotto',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 1),
                              Text(
                                mottoYear,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 34,
                                  height: 1,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(
                          Icons.chevron_right_rounded,
                          color: Colors.white,
                          size: 36,
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
    );
  }
}
