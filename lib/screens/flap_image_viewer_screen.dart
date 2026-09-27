import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../data/app_store.dart';

class FlapImageViewerScreen extends StatefulWidget {
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
  State<FlapImageViewerScreen> createState() => _FlapImageViewerScreenState();
}

class _FlapImageViewerScreenState extends State<FlapImageViewerScreen> {
  bool sharing = false;

  String _extension(String mimeType) {
    switch (mimeType) {
      case 'image/png':
        return 'png';
      case 'image/webp':
        return 'webp';
      case 'image/gif':
        return 'gif';
      default:
        return 'jpg';
    }
  }

  String _safeName(String value) {
    final cleaned = value
        .replaceAll(RegExp(r'[^A-Za-z0-9ÄÖÜäöü_-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    return cleaned.isEmpty ? 'FLAPAMAMAKU' : cleaned;
  }

  Future<void> _shareCurrent() async {
    if (sharing || widget.widget.imageUrl.isEmpty) return;
    setState(() => sharing = true);
    try {
      final store = AppStoreScope.of(context);
      final downloaded = await store.api.downloadImage(widget.widget.imageUrl);
      final extension = _extension(downloaded.mimeType);
      final directory = await getTemporaryDirectory();
      final file = File(
        '${directory.path}/${_safeName(widget.title)}.$extension',
      );
      await file.writeAsBytes(downloaded.bytes, flush: true);
      await SharePlus.instance.share(
        ShareParams(
          title: 'Bild speichern oder teilen',
          files: [XFile(file.path, mimeType: downloaded.mimeType)],
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bild konnte nicht exportiert werden: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => sharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final headers = AppStoreScope.of(context).api.authHeaders;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: Text(
          widget.title,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          if (widget.imageUrl.isNotEmpty)
            IconButton(
              tooltip: 'Speichern / Teilen',
              onPressed: sharing ? null : _shareCurrent,
              icon: sharing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: InteractiveViewer(
              minScale: 1,
              maxScale: 5,
              child: Center(
                child: widget.imageUrl.isNotEmpty
                    ? Image.network(
                        widget.imageUrl,
                        headers: headers,
                        width: double.infinity,
                        fit: BoxFit.contain,
                        errorBuilder: (_, __, ___) => widget.imageAsset.isNotEmpty
                            ? Image.asset(
                                widget.imageAsset,
                                width: double.infinity,
                                fit: BoxFit.contain,
                              )
                            : const Text(
                                'Bild konnte nicht geladen werden.',
                                style: TextStyle(color: Colors.white70),
                              ),
                      )
                    : Image.asset(
                        widget.imageAsset,
                        width: double.infinity,
                        fit: BoxFit.contain,
                      ),
              ),
            ),
          ),
          if (widget.imageUrl.isNotEmpty)
            Positioned(
              right: 18,
              bottom: 24,
              child: SafeArea(
                top: false,
                child: FloatingActionButton.extended(
                  heroTag: 'image-export',
                  onPressed: sharing ? null : _shareCurrent,
                  icon: const Icon(Icons.ios_share_rounded),
                  label: const Text('Export / Teilen'),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
