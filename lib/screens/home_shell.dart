import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../data/app_store.dart';
import '../data/message_api.dart';
import 'start_screen.dart';
import 'news_screen.dart';
import 'events_screen.dart';
import 'remote_content_screen.dart';
import 'more_screen.dart';
import 'messages_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final push = AppStoreScope.of(context).pushService;
    push.onRoute = _openPushRoute;
    final pending = push.takePendingRoute();
    if (pending != null && pending.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _openPushRoute(pending);
      });
    }
  }

  List<_NavEntry> _entries(AppStore store) => [
        const _NavEntry(
          route: '/',
          page: StartScreen(),
          destination: NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Start',
          ),
        ),
        if (store.showNews)
          const _NavEntry(
            route: '/news',
            page: NewsScreen(),
            destination: NavigationDestination(
              icon: Icon(Icons.article_outlined),
              selectedIcon: Icon(Icons.article_rounded),
              label: 'News',
            ),
          ),
        if (store.showEvents)
          const _NavEntry(
            route: '/events',
            page: EventsScreen(),
            destination: NavigationDestination(
              icon: Icon(Icons.calendar_month_outlined),
              selectedIcon: Icon(Icons.calendar_month_rounded),
              label: 'Termine',
            ),
          ),
        if (store.showGallery)
          const _NavEntry(
            route: '/gallery',
            page: RemoteContentScreen.archiveStyle(
              section: 'gallery',
              title: 'Galerie',
              emptyText: 'Noch keine Fotos oder Alben hinterlegt.',
              icon: Icons.photo_library_outlined,
              individualImages: true,
            ),
            destination: NavigationDestination(
              icon: Icon(Icons.photo_outlined),
              selectedIcon: Icon(Icons.photo_rounded),
              label: 'Galerie',
            ),
          ),
        if (store.showLinks)
          const _NavEntry(
            route: '/whatsapp',
            page: SizedBox.shrink(),
            isAction: true,
            destination: NavigationDestination(
              icon: Icon(Icons.chat_outlined),
              selectedIcon: Icon(Icons.chat_rounded),
              label: 'WhatsApp',
            ),
          ),
        const _NavEntry(
          route: '/more',
          page: MoreScreen(),
          destination: NavigationDestination(
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(Icons.more_horiz_rounded),
            label: 'Mehr',
          ),
        ),
      ];

  void _openPushRoute(String route) {
    if (!mounted) return;
    if (route == '/messages') {
      Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const MessagesScreen()),
      );
      return;
    }
    final store = AppStoreScope.of(context);
    final entries = _entries(store);
    final nextIndex = entries.indexWhere((entry) => entry.route == route);
    if (nextIndex < 0 || entries[nextIndex].isAction) return;
    if (index != nextIndex) {
      setState(() => index = nextIndex);
    }
  }

  Future<void> _openWhatsAppGroup() async {
    final store = AppStoreScope.of(context);
    if (!store.showLinks) return;

    final link = store
        .contentFor('whatsapp')
        .map((item) => item.linkUrl.trim())
        .firstWhere((value) => value.isNotEmpty, orElse: () => '');

    if (link.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('WhatsApp-Einladungslink ist noch nicht hinterlegt.'),
        ),
      );
      return;
    }

    final uri = Uri.tryParse(link);
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('WhatsApp-Gruppenlink ist ungültig.')),
      );
      return;
    }

    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('WhatsApp konnte nicht geöffnet werden.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final entries = _entries(store);
    final safeIndex = index.clamp(0, entries.length - 1);
    if (safeIndex != index) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => index = safeIndex);
      });
    }

    final body = SafeArea(top: false, child: entries[safeIndex].page);

    return Scaffold(
      body: safeIndex == 0 && store.serverConfigured && store.isAuthenticated
          ? Stack(
              children: [
                body,
                Positioned(
                  left: 16,
                  right: 16,
                  top: MediaQuery.of(context).padding.top + 94,
                  child: FutureBuilder<int>(
                    future: MessageApi(store.api).unreadCount(),
                    builder: (context, snapshot) {
                      final unread = snapshot.data ?? 0;
                      if (unread <= 0) return const SizedBox.shrink();
                      return Material(
                        color: const Color(0xFF191B1E),
                        elevation: 8,
                        borderRadius: BorderRadius.circular(16),
                        clipBehavior: Clip.antiAlias,
                        child: InkWell(
                          onTap: () => Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const MessagesScreen(),
                            ),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 12,
                            ),
                            child: Row(
                              children: [
                                Container(
                                  width: 42,
                                  height: 42,
                                  decoration: BoxDecoration(
                                    color: store.themeColor,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Icon(
                                    Icons.notifications_active_rounded,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        'Neue Mitteilungen',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w900,
                                          fontSize: 16,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        '$unread ungelesene ${unread == 1 ? 'Mitteilung' : 'Mitteilungen'}',
                                        style: const TextStyle(
                                          color: Colors.white70,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  constraints: const BoxConstraints(
                                    minWidth: 28,
                                    minHeight: 28,
                                  ),
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFD7B45A),
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: Text(
                                    unread.toString(),
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      color: Colors.black,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 4),
                                const Icon(
                                  Icons.chevron_right_rounded,
                                  color: Colors.white70,
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            )
          : body,
      bottomNavigationBar: NavigationBar(
        height: 74,
        selectedIndex: safeIndex,
        onDestinationSelected: (value) {
          final entry = entries[value];
          if (entry.isAction) {
            _openWhatsAppGroup();
            return;
          }
          setState(() => index = value);
        },
        destinations: entries.map((entry) => entry.destination).toList(),
      ),
    );
  }
}

class _NavEntry {
  final String route;
  final Widget page;
  final NavigationDestination destination;
  final bool isAction;

  const _NavEntry({
    required this.route,
    required this.page,
    required this.destination,
    this.isAction = false,
  });
}
