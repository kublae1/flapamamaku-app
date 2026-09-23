import 'package:flutter/material.dart';

class YearMottoScreen extends StatefulWidget {
  const YearMottoScreen({super.key});

  @override
  State<YearMottoScreen> createState() => _YearMottoScreenState();
}

class _YearMottoScreenState extends State<YearMottoScreen> {
  static const _images = [
    'assets/images/year_motto_pig_rockers.jpg',
    'assets/images/archive_top_hats_night.jpg',
  ];

  int _page = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: const Text('Aktuelles Sujet')),
      body: Stack(
        children: [
          PageView.builder(
            itemCount: _images.length,
            onPageChanged: (value) => setState(() => _page = value),
            itemBuilder: (_, index) => InteractiveViewer(
              minScale: 1,
              maxScale: 4,
              child: Center(
                child: Image.asset(
                  _images[index],
                  fit: BoxFit.contain,
                  width: double.infinity,
                ),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 28,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _images.length,
                (index) => Container(
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  width: index == _page ? 20 : 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: index == _page ? Colors.white : Colors.white54,
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
