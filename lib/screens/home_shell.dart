import 'package:flutter/material.dart';
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
      _ => 0,
    };
    if (index != nextIndex) {
      setState(() => index = nextIndex);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(top: false, child: pages[index]),
      bottomNavigationBar: NavigationBar(
        height: 74,
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
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
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(Icons.more_horiz_rounded),
            label: 'Mehr',
          ),
        ],
      ),
    );
  }
}
