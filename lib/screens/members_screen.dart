import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';
import 'content_detail_screens.dart';

class MembersScreen extends StatefulWidget {
  const MembersScreen({super.key});

  @override
  State<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends State<MembersScreen> {
  bool searching = false;
  String query = '';

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final filtered = store.members.where((member) {
      final value = query.trim().toLowerCase();
      if (value.isEmpty) return true;
      return member.name.toLowerCase().contains(value) ||
          member.role.toLowerCase().contains(value) ||
          member.occupation.toLowerCase().contains(value) ||
          member.employer.toLowerCase().contains(value);
    }).toList();

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: searching
            ? TextField(
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  hintText: 'Mitglied suchen',
                  hintStyle: TextStyle(color: Colors.white54),
                  border: InputBorder.none,
                ),
                onChanged: (value) => setState(() => query = value),
              )
            : const Text(
                'Mitglieder',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
        actions: [
          IconButton(
            onPressed: () => setState(() {
              searching = !searching;
              if (!searching) query = '';
            }),
            icon: Icon(searching ? Icons.close_rounded : Icons.search_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: filtered.isEmpty
            ? ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(28),
                children: const [
                  SizedBox(height: 100),
                  Icon(Icons.groups_outlined, color: Colors.white54, size: 64),
                  SizedBox(height: 18),
                  Text(
                    'Keine Mitglieder gefunden',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white70, fontSize: 17),
                  ),
                ],
              )
            : ListView.separated(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                itemCount: filtered.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (_, i) {
                  final member = filtered[i];
                  return Material(
                    color: const Color(0xFF191B1E),
                    borderRadius: BorderRadius.circular(18),
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => MemberDetailScreen(member: member),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            CircleAvatar(
                              radius: 31,
                              backgroundColor: FlapBrand.burgundy,
                              backgroundImage: member.photoUrl.isNotEmpty
                                  ? NetworkImage(
                                      member.photoUrl,
                                      headers: store.api.authHeaders,
                                    )
                                  : null,
                              child: member.photoUrl.isEmpty
                                  ? Text(
                                      member.name.characters.first,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w900,
                                        fontSize: 21,
                                      ),
                                    )
                                  : null,
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    member.name,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w900,
                                      fontSize: 17,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    member.occupation.isEmpty
                                        ? member.role
                                        : '${member.role} · ${member.occupation}',
                                    style: const TextStyle(
                                      color: FlapBrand.gold,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  if (member.since.isNotEmpty) ...[
                                    const SizedBox(height: 3),
                                    Text(
                                      member.since,
                                      style: const TextStyle(
                                        color: Colors.white54,
                                      ),
                                    ),
                                  ],
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
                  );
                },
              ),
      ),
    );
  }
}
