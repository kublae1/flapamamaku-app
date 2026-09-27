import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../data/app_store.dart';
import 'start_screen.dart';
import 'news_screen.dart';
import 'events_screen.dart';
import 'remote_content_screen.dart';
import 'more_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;

  final pages = const [
    StartScreen(),
    NewsScreen(),
    EventsScreen(),
    RemoteContentScreen.archiveStyle(
      section: 'gallery',
      title: 'Galerie',
      emptyText: 'Noch keine Fotos oder Alben hinterlegt.',
      icon: Icons.photo_library_outlined,
      individualImages: true,
    ),
    SizedBox.shrink(),
    MoreScreen(),
  ];

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

  void _openPushRoute(String route) {
    if (!mounted) return;
    final nextIndex = switch (route) {
      '/news' => 1,
      '/events' => 2,
      '/gallery' => 3,
      '/more' => 5,
      _ => 0,
    };
    if (index != nextIndex) {
      setState(() => index = nextIndex);
    }
  }

  Future<void> _openWhatsAppGroup() async {
    final store = AppStoreScope.of(context);
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
    return Scaffold(
      body: SafeArea(top: false, child: pages[index]),
      bottomNavigationBar: NavigationBar(
        height: 74,
        selectedIndex: index,
        onDestinationSelected: (value) {
          if (value == 4) {
            _openWhatsAppGroup();
            return;
          }
          setState(() => index = value);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Start',
          ),
          NavigationDestination(
            icon: Icon(Icons.article_outlined),
            selectedIcon: Icon(Icons.article_rounded),
            label: 'News',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month_rounded),
            label: 'Termine',
          ),
          NavigationDestination(
            icon: Icon(Icons.photo_outlined),
            selectedIcon: Icon(Icons.photo_rounded),
            label: 'Galerie',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_outlined),
            selectedIcon: Icon(Icons.chat_rounded),
            label: 'WhatsApp',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(Icons.more_horiz_rounded),
            label: 'Mehr',
          ),
        ],
      ),
    );
  }
}
