import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';
import 'admin_screen.dart';
import 'members_screen.dart';
import 'remote_content_screen.dart';
import 'settings_screen.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Mehr',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 30),
          children: [
            const _SectionLabel('GRUPPE'),
            _MockupMenuCard(
              icon: Icons.groups_rounded,
              title: 'Mitglieder',
              subtitle: 'Infos, Kontakte und Mitgliederübersicht',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const MembersScreen()),
              ),
            ),
            if (store.canAdminister)
              _MockupMenuCard(
                icon: Icons.admin_panel_settings_rounded,
                title: 'Administration',
                subtitle: 'Freigegebene Bereiche verwalten',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AdminScreen()),
                ),
              ),
            const SizedBox(height: 18),
            const _SectionLabel('INHALTE'),
            _remoteSection(
              context,
              section: 'sujet',
              icon: Icons.auto_awesome_rounded,
              title: 'Sujet nächstes Jahr',
              subtitle: 'Fotos und Sujet für die nächste Fasnacht',
              emptyText: 'Noch kein Sujet für nächstes Jahr hinterlegt.',
            ),
            _remoteSection(
              context,
              section: 'archive',
              icon: Icons.history_rounded,
              title: 'Vergangene Sujet',
              subtitle: 'Frühere Sujets und Bilder',
              emptyText: 'Noch keine vergangenen Sujets hinterlegt.',
            ),
            _remoteSection(
              context,
              section: 'photos',
              icon: Icons.photo_library_rounded,
              title: 'Fotoalben',
              subtitle: 'Anlässe, Umzüge und gemeinsame Aktivitäten',
              emptyText: 'Noch keine Fotoalben hinterlegt.',
            ),
            _remoteSection(
              context,
              section: 'documents',
              icon: Icons.description_rounded,
              title: 'Dokumente',
              subtitle: 'Protokolle, Reglemente und interne Informationen',
              emptyText: 'Noch keine Dokumente hinterlegt.',
            ),
            _remoteSection(
              context,
              section: 'polls',
              icon: Icons.how_to_vote_rounded,
              title: 'Umfragen',
              subtitle: 'Interne Umfragen und Abstimmungen',
              emptyText: 'Noch keine Umfragen hinterlegt.',
            ),
            _remoteSection(
              context,
              section: 'links',
              icon: Icons.link_rounded,
              title: 'Links',
              subtitle: 'Nützliche Webseiten und Verweise',
              emptyText: 'Noch keine Links hinterlegt.',
            ),
            const SizedBox(height: 18),
            const _SectionLabel('APP'),
            _MockupMenuCard(
              icon: Icons.settings_rounded,
              title: 'Einstellungen',
              subtitle: 'Biometrie und App-Einstellungen',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              ),
            ),
            if (store.serverConfigured && store.isAuthenticated) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: const Color(0xFF191B1E),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0x22FFFFFF)),
                ),
                child: Row(
                  children: [
                    const CircleAvatar(
                      backgroundColor: FlapBrand.burgundy,
                      foregroundColor: Colors.white,
                      child: Icon(Icons.person_rounded),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            store.signedInName.isEmpty
                                ? 'Angemeldet'
                                : store.signedInName,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                              fontSize: 16,
                            ),
                          ),
                          const Text(
                            'Benutzerkonto',
                            style: TextStyle(color: Colors.white60),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Abmelden',
                      onPressed: store.logout,
                      color: Colors.white70,
                      icon: const Icon(Icons.logout_rounded),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _remoteSection(
    BuildContext context, {
    required String section,
    required IconData icon,
    required String title,
    required String subtitle,
    required String emptyText,
  }) {
    final count = AppStoreScope.of(context).contentFor(section).length;
    return _MockupMenuCard(
      icon: icon,
      title: title,
      subtitle: count == 0 ? subtitle : '$count Einträge · $subtitle',
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => section == 'sujet' ||
                  section == 'archive' ||
                  section == 'photos'
              ? RemoteContentScreen.archiveStyle(
                  section: section,
                  title: title,
                  emptyText: emptyText,
                  icon: icon,
                )
              : RemoteContentScreen(
                  section: section,
                  title: title,
                  emptyText: emptyText,
                  icon: icon,
                ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 4, 10),
      child: Text(
        text,
        style: const TextStyle(
          color: FlapBrand.gold,
          fontWeight: FontWeight.w900,
          fontSize: 11,
          letterSpacing: 1.5,
        ),
      ),
    );
  }
}

class _MockupMenuCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _MockupMenuCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(18),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 10, 14),
            child: Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: FlapBrand.burgundy,
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Icon(icon, color: Colors.white, size: 27),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        subtitle,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white60,
                          height: 1.25,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white54,
                  size: 28,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
