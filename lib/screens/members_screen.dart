import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import 'content_detail_screens.dart';

enum _MemberSort { manual, name, role, since }

class MembersScreen extends StatefulWidget {
  const MembersScreen({super.key});

  @override
  State<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends State<MembersScreen> {
  String query = '';
  int? selectedFilterId;
  String selectedLetter = '';
  _MemberSort sort = _MemberSort.manual;

  List<MemberItem> _filtered(List<MemberItem> source) {
    final q = query.trim().toLowerCase();
    final items = source.where((member) {
      if (selectedFilterId != null && !member.filterIds.contains(selectedFilterId)) {
        return false;
      }
      if (selectedLetter.isNotEmpty &&
          !member.name.trim().toUpperCase().startsWith(selectedLetter)) {
        return false;
      }
      if (q.isEmpty) return true;
      return [
        member.name,
        member.role,
        member.occupation,
        member.employer,
        member.since,
      ].any((value) => value.toLowerCase().contains(q));
    }).toList();

    items.sort((a, b) {
      switch (sort) {
        case _MemberSort.manual:
          final byOrder = a.sortOrder.compareTo(b.sortOrder);
          return byOrder != 0
              ? byOrder
              : a.name.toLowerCase().compareTo(b.name.toLowerCase());
        case _MemberSort.name:
          return a.name.toLowerCase().compareTo(b.name.toLowerCase());
        case _MemberSort.role:
          final byRole = a.role.toLowerCase().compareTo(b.role.toLowerCase());
          return byRole != 0
              ? byRole
              : a.name.toLowerCase().compareTo(b.name.toLowerCase());
        case _MemberSort.since:
          final bySince = a.since.toLowerCase().compareTo(b.since.toLowerCase());
          return bySince != 0
              ? bySince
              : a.name.toLowerCase().compareTo(b.name.toLowerCase());
      }
    });
    return items;
  }

  String _sortLabel(_MemberSort value) {
    switch (value) {
      case _MemberSort.manual:
        return 'Docker-Reihenfolge';
      case _MemberSort.name:
        return 'Nachname / Name';
      case _MemberSort.role:
        return 'Funktion';
      case _MemberSort.since:
        return 'Eintritt';
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final activeFilters = store.memberFilters
        .where((filter) => filter.active)
        .toList()
      ..sort((a, b) => a.sortOrder.compareTo(b.sortOrder));
    final items = _filtered(store.members);
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Mitglieder',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          PopupMenuButton<_MemberSort>(
            tooltip: 'Sortieren',
            initialValue: sort,
            icon: const Icon(Icons.sort_rounded),
            onSelected: (value) => setState(() => sort = value),
            itemBuilder: (_) => _MemberSort.values
                .map(
                  (value) => PopupMenuItem(
                    value: value,
                    child: Text(_sortLabel(value)),
                  ),
                )
                .toList(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: Stack(
          children: [
            ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 14, 38, 28),
              children: [
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF191B1E),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0x18FFFFFF)),
                  ),
                  child: TextField(
                    onChanged: (value) => setState(() {
                      query = value;
                      selectedLetter = '';
                    }),
                    style: const TextStyle(color: Colors.white),
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search_rounded, color: FlapBrand.gold),
                      hintText: 'Mitglied suchen …',
                      hintStyle: TextStyle(color: Colors.white38),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ChoiceChip(
                            label: const Text('Alle'),
                            selected: selectedFilterId == null,
                            onSelected: (_) => setState(() => selectedFilterId = null),
                          ),
                          ...activeFilters.map(
                            (filter) => ChoiceChip(
                              label: Text(filter.label),
                              selected: selectedFilterId == filter.id,
                              onSelected: (_) => setState(() {
                                selectedFilterId =
                                    selectedFilterId == filter.id ? null : filter.id;
                              }),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 12),
                      decoration: BoxDecoration(
                        color: FlapBrand.burgundy,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        children: [
                          Text(
                            '${items.length}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const Text(
                            'Mitglieder',
                            style: TextStyle(color: Colors.white70, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (selectedLetter.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: ActionChip(
                      avatar: const Icon(Icons.close_rounded, size: 17),
                      label: Text('Buchstabe $selectedLetter'),
                      onPressed: () => setState(() => selectedLetter = ''),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                if (items.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 80),
                    child: Column(
                      children: [
                        Icon(Icons.groups_outlined, color: Colors.white38, size: 64),
                        SizedBox(height: 16),
                        Text(
                          'Keine Mitglieder gefunden',
                          style: TextStyle(color: Colors.white60, fontSize: 17),
                        ),
                      ],
                    ),
                  )
                else
                  ...items.map(
                    (member) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _MemberCard(
                        member: member,
                        headers: store.api.authHeaders,
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => MemberDetailScreen(member: member),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            Positioned(
              right: 2,
              top: 178,
              bottom: 18,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    for (final letter in letters.characters)
                      GestureDetector(
                        onTap: () => setState(() {
                          selectedLetter =
                              selectedLetter == letter ? '' : letter;
                        }),
                        child: Container(
                          width: 28,
                          height: 22,
                          alignment: Alignment.center,
                          child: Text(
                            letter,
                            style: TextStyle(
                              color: selectedLetter == letter
                                  ? FlapBrand.gold
                                  : Colors.white38,
                              fontSize: 11,
                              fontWeight: selectedLetter == letter
                                  ? FontWeight.w900
                                  : FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MemberCard extends StatelessWidget {
  final MemberItem member;
  final Map<String, String> headers;
  final VoidCallback onTap;

  const _MemberCard({
    required this.member,
    required this.headers,
    required this.onTap,
  });

  String get _subtitle {
    final values = [
      if (member.role.trim().isNotEmpty) member.role.trim(),
      if (member.occupation.trim().isNotEmpty) member.occupation.trim(),
    ];
    return values.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF191B1E),
      borderRadius: BorderRadius.circular(18),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 8, 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Hero(
                tag: 'member-photo-${member.id ?? member.name}',
                child: Container(
                  width: 82,
                  height: 96,
                  decoration: BoxDecoration(
                    color: FlapBrand.burgundy,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: member.photoUrl.isNotEmpty
                      ? Image.network(
                          member.photoUrl,
                          headers: headers,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => _Initial(member.name),
                        )
                      : _Initial(member.name),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        member.name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      if (_subtitle.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          _subtitle,
                          style: const TextStyle(
                            color: FlapBrand.gold,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                      if (member.since.trim().isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(
                              Icons.groups_2_outlined,
                              color: Colors.white38,
                              size: 17,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                member.since,
                                style: const TextStyle(color: Colors.white60),
                              ),
                            ),
                          ],
                        ),
                      ],
                      if (member.employer.trim().isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          member.employer,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 32),
                child: Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white38,
                  size: 28,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Initial extends StatelessWidget {
  final String name;

  const _Initial(this.name);

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        name.trim().isEmpty ? '?' : name.trim().characters.first.toUpperCase(),
        style: const TextStyle(
          color: Colors.white,
          fontSize: 30,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
