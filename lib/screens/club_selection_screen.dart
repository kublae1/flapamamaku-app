import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

class ClubSelectionScreen extends StatefulWidget {
  final bool returnAfterSelection;
  final bool allowBack;

  const ClubSelectionScreen({
    super.key,
    this.returnAfterSelection = false,
    this.allowBack = false,
  });

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
    if (!mounted) return;

    if (ok) {
      if (widget.returnAfterSelection && Navigator.of(context).canPop()) {
        Navigator.of(context).pop(true);
      }
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          store.authError ?? 'Verein konnte nicht geöffnet werden.',
        ),
      ),
    );
    setState(() => _loadingClubId = null);
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final clubs = store.accessibleClubs;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        automaticallyImplyLeading: widget.allowBack,
        title: const Text(
          'Verein auswählen',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          if (!widget.allowBack)
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
          Text(
            widget.returnAfterSelection
                ? 'Aktuell geöffnet: ${store.currentClubName}. Wähle einen anderen Verein.'
                : 'Du bist mehreren Vereinen zugeordnet. Wähle den Verein, den du jetzt öffnen möchtest.',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 16,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 18),
          for (final club in clubs) ...[
            _ClubCard(
              club: club,
              current: _clubId(club) == store.currentClubId,
              loading: _loadingClubId == _clubId(club),
              onTap: () {
                final id = _clubId(club);
                if (id != null) _selectClub(id);
              },
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }

  int? _clubId(Map<String, dynamic> club) {
    final rawId = club['id'];
    return rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
  }
}

class _ClubCard extends StatelessWidget {
  final Map<String, dynamic> club;
  final bool current;
  final bool loading;
  final VoidCallback onTap;

  const _ClubCard({
    required this.club,
    required this.current,
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
                    if (current)
                      const Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Text(
                          'Aktuell geöffnet',
                          style: TextStyle(
                            color: FlapBrand.gold,
                            fontWeight: FontWeight.w800,
                            fontSize: 12,
                          ),
                        ),
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
              else if (current)
                const Icon(
                  Icons.check_circle_rounded,
                  color: FlapBrand.gold,
                  size: 27,
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
