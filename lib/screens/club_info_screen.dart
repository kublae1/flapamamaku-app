import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../widgets/offline_network_image.dart';
import '../theme/flap_brand.dart';

class ClubInfoScreen extends StatelessWidget {
  const ClubInfoScreen({super.key});

  Future<void> _launch(BuildContext context, String value) async {
    final uri = Uri.tryParse(value.trim());
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Link konnte nicht geöffnet werden.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final hasDescription = store.clubDescription.isNotEmpty;
    final hasContact = store.contactEmail.isNotEmpty ||
        store.contactPhone.isNotEmpty ||
        store.clubAddress.isNotEmpty ||
        store.websiteUrl.isNotEmpty;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: Text(
          store.appName,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 22, 18, 34),
        children: [
          if (store.appLogoUrl.isNotEmpty)
            Center(
              child: Container(
                width: 120,
                height: 120,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: OfflineNetworkImage(
                  store.appLogoUrl,
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) =>
                      const Icon(Icons.groups_rounded, size: 58),
                ),
              ),
            ),
          if (store.appLogoUrl.isNotEmpty) const SizedBox(height: 18),
          Text(
            store.appName,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 26,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (store.appSubtitle.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              store.appSubtitle,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: FlapBrand.gold,
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
          if (hasDescription) ...[
            const SizedBox(height: 24),
            _DarkCard(
              child: Text(
                store.clubDescription,
                style: const TextStyle(
                  color: Colors.white70,
                  height: 1.55,
                  fontSize: 16,
                ),
              ),
            ),
          ],
          if (hasContact) ...[
            const SizedBox(height: 18),
            const Text(
              'KONTAKT',
              style: TextStyle(
                color: FlapBrand.gold,
                fontSize: 11,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 10),
            _DarkCard(
              child: Column(
                children: [
                  if (store.clubAddress.isNotEmpty)
                    _InfoRow(
                      icon: Icons.location_on_outlined,
                      title: 'Adresse',
                      value: store.clubAddress,
                    ),
                  if (store.contactEmail.isNotEmpty)
                    _InfoRow(
                      icon: Icons.email_outlined,
                      title: 'E-Mail',
                      value: store.contactEmail,
                      onTap: () => _launch(
                        context,
                        'mailto:${store.contactEmail}',
                      ),
                    ),
                  if (store.contactPhone.isNotEmpty)
                    _InfoRow(
                      icon: Icons.phone_outlined,
                      title: 'Telefon',
                      value: store.contactPhone,
                      onTap: () => _launch(
                        context,
                        'tel:${store.contactPhone.replaceAll(' ', '')}',
                      ),
                    ),
                  if (store.websiteUrl.isNotEmpty)
                    _InfoRow(
                      icon: Icons.language_rounded,
                      title: 'Webseite',
                      value: store.websiteUrl,
                      onTap: () => _launch(context, store.websiteUrl),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _DarkCard extends StatelessWidget {
  final Widget child;
  const _DarkCard({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0x22FFFFFF)),
      ),
      child: child,
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;
  final VoidCallback? onTap;

  const _InfoRow({
    required this.icon,
    required this.title,
    required this.value,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: FlapBrand.gold),
      title: Text(
        title,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: Text(
        value,
        style: const TextStyle(color: Colors.white70),
      ),
      trailing: onTap == null
          ? null
          : const Icon(Icons.open_in_new_rounded, color: Colors.white38),
      onTap: onTap,
    );
  }
}
