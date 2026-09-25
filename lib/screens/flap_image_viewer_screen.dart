import 'package:flutter/material.dart';

import '../data/app_store.dart';

class FlapImageViewerScreen extends StatelessWidget {
  final String title;
  final String imageUrl;
  final String imageAsset;

  const FlapImageViewerScreen({
    required this.title,
    this.imageUrl = '',
    this.imageAsset = '',
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final headers = AppStoreScope.of(context).api.authHeaders;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: InteractiveViewer(
        minScale: 1,
        maxScale: 5,
        child: Center(
          child: imageUrl.isNotEmpty
              ? Image.network(
                  imageUrl,
                  headers: headers,
                  width: double.infinity,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => imageAsset.isNotEmpty
                      ? Image.asset(
                          imageAsset,
                          width: double.infinity,
                          fit: BoxFit.contain,
                        )
                      : const Text(
                          'Bild konnte nicht geladen werden.',
                          style: TextStyle(color: Colors.white70),
                        ),
                )
              : Image.asset(
                  imageAsset,
                  width: double.infinity,
                  fit: BoxFit.contain,
                ),
        ),
      ),
    );
  }
}
