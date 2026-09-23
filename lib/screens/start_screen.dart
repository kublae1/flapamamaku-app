import 'dart:async';
import 'package:flutter/material.dart';

import '../models/app_data.dart';
import '../widgets/section_title.dart';
import 'year_motto_screen.dart';
import 'archive_screen.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverAppBar(
          expandedHeight: 285,
          pinned: true,
          backgroundColor: const Color(0xFF8A101B),
          title: const Text('FLAPAMAMAKU'),
          flexibleSpace: FlexibleSpaceBar(
            background: Stack(
              fit: StackFit.expand,
              children: [
                Image.asset('assets/images/hero_fireworks.jpg', fit: BoxFit.cover),
                const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Colors.black12, Colors.black87],
                    ),
                  ),
                ),
                const Positioned(
                  left: 22,
                  right: 22,
                  bottom: 22,
                  child: Text(
                    'Zäme ade Fasnacht Luzern!',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 29,
                      fontWeight: FontWeight.w800,
                    ),
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
                borderRadius: BorderRadius.circular(18),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const YearMottoScreen()),
                ),
                child: const SujetSlider(),
              ),
              const SizedBox(height: 22),
              const SectionTitle('Aktuelle News', action: 'Alle'),
              const SizedBox(height: 8),
              Card(
                child: ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.campaign)),
                  title: Text(newsItems.first.title),
                  subtitle: Text('${newsItems.first.date}\n${newsItems.first.text}'),
                  isThreeLine: true,
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
              const SizedBox(height: 20),
              const SectionTitle('Nächste Termine', action: 'Alle'),
              const SizedBox(height: 8),
              ...eventItems.take(2).map(
                (e) => Card(
                  child: ListTile(
                    leading: SizedBox(
                      width: 48,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(e.day, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                          Text(e.month),
                        ],
                      ),
                    ),
                    title: Text(e.title),
                    subtitle: Text('${e.location} · ${e.time}'),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Card(
                child: ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.photo_library_outlined)),
                  title: const Text('Archiv', style: TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: const Text('Frühere Sujets, Mottos und Erinnerungen'),
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
