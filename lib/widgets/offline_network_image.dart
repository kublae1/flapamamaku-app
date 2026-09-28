import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

class OfflineNetworkImage extends StatelessWidget {
  final String imageUrl;
  final Map<String, String>? headers;
  final BoxFit? fit;
  final double? width;
  final double? height;
  final Alignment alignment;
  final FilterQuality filterQuality;
  final Widget Function(BuildContext, Object, StackTrace?)? errorBuilder;

  const OfflineNetworkImage(
    this.imageUrl, {
    this.headers,
    this.fit,
    this.width,
    this.height,
    this.alignment = Alignment.center,
    this.filterQuality = FilterQuality.low,
    this.errorBuilder,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return CachedNetworkImage(
      imageUrl: imageUrl,
      httpHeaders: headers,
      fit: fit,
      width: width,
      height: height,
      alignment: alignment,
      filterQuality: filterQuality,
      useOldImageOnUrlChange: true,
      fadeInDuration: Duration.zero,
      fadeOutDuration: Duration.zero,
      errorWidget: errorBuilder == null
          ? null
          : (context, _, error) => errorBuilder!(context, error, null),
    );
  }
}
