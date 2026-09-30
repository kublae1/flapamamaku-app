import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

class ClubSelectionScreen extends StatefulWidget {
  const ClubSelectionScreen({super.key});

  @override
  State<ClubSelectionScreen> createState() => _ClubSelectionScreenState();
}

class _ClubSelectionScreenState extends State<ClubSelectionScreen> {
  int? _loadingClubId;

  Future<void> _selectClub(int clubId) async {
    if (_loadingClubId != null) return;
    setState(() => _loadingClubId = clubId);
    final store = AppStoreScope.of(context);
    final ok = await store.selectClub(clubId);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            store.authError ?? 'Verein konnte nicht geöffnet werden.',
          ),
        ),
      );
      setState(() => _loadingClubId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final clubs = store.accessibleClubs;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text(
          'Verein auswählen',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          IconButton(
            tooltip: 'Abmelden',
            onPressed: _loadingClubId == null ? store.logout : null,
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 24, 16, 32),
        children: [
          const Text(
            'Du bist mehreren Vereinen zugeordnet. Wähle den Verein, den du jetzt öffnen möchtest.',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 16,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 18),
          for (final club in clubs) ...[
            _ClubCard(
              club: club,
              loading: _loadingClubId ==
                  (club['id'] is int
                      ? club['id'] as int
                      : int.tryParse(club['id']?.toString() ?? '')),
              onTap: () {
                final rawId = club['id'];
                final id =
                    rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
                if (id != null) _selectClub(id);
              },
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _ClubCard extends StatelessWidget {
  final Map<String, dynamic> club;
  final bool loading;
  final VoidCallback onTap;

  const _ClubCard({
    required this.club,
    required this.loading,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final colorText = club['primary_color']?.toString() ?? '';
    final match = RegExp(r'^#([0-9A-Fa-f]{6})$').firstMatch(colorText);
    final color = match == null
        ? Theme.of(context).colorScheme.primary
        : Color(int.parse('FF${match.group(1)!}', radix: 16));

    return Material(
      color: const Color(0xFF191B1E),
      borderRadius: BorderRadius.circular(18),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: loading ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(
                  Icons.groups_rounded,
                  color: Colors.white,
                  size: 28,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      club['name']?.toString() ?? 'Verein',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 17,
                      ),
                    ),
                    if ((club['short_name']?.toString() ?? '').isNotEmpty)
                      Text(
                        club['short_name'].toString(),
                        style: const TextStyle(color: Colors.white54),
                      ),
                  ],
                ),
              ),
              if (loading)
                const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                )
              else
                const Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white54,
                  size: 28,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
