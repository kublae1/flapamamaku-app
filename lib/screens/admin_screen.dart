import 'package:flutter/material.dart';
import '../data/app_store.dart';
import '../models/app_data.dart';

class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  String _dateLabel(DateTime value) {
    final day = value.day.toString().padLeft(2, '0');
    final month = value.month.toString().padLeft(2, '0');
    return '$day.$month.${value.year}';
  }

  Future<void> _addNews(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final now = DateTime.now();
    final title = TextEditingController();
    final text = TextEditingController();
    final date = TextEditingController(text: _dateLabel(now));
    String imageAsset = '';

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Neue News'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: title,
                  decoration: const InputDecoration(labelText: 'Titel'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: text,
                  minLines: 4,
                  maxLines: 8,
                  decoration: const InputDecoration(labelText: 'Text'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: date,
                  decoration: const InputDecoration(labelText: 'Datum'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: imageAsset,
                  decoration: const InputDecoration(labelText: 'Foto optional'),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('Kein Foto')),
                    DropdownMenuItem(
                      value: 'assets/images/year_motto_pig_rockers.jpg',
                      child: Text('Schweine Rocker'),
                    ),
                    DropdownMenuItem(
                      value: 'assets/images/archive_top_hats_night.jpg',
                      child: Text('Zylinder'),
                    ),
                    DropdownMenuItem(
                      value: 'assets/images/archive_vikings_bar.jpg',
                      child: Text('Wikinger'),
                    ),
                    DropdownMenuItem(
                      value: 'assets/images/hero_fireworks.jpg',
                      child: Text('Feuerwerk'),
                    ),
                  ],
                  onChanged: (value) => setDialogState(
                    () => imageAsset = value ?? '',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Abbrechen'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Speichern'),
            ),
          ],
        ),
      ),
    );

    if (save == true &&
        title.text.trim().isNotEmpty &&
        text.text.trim().isNotEmpty) {
      store.addNews(
        NewsItem(
          date.text.trim(),
          title.text.trim(),
          text.text.trim(),
          createdAt: now.toIso8601String(),
          imageAsset: imageAsset,
        ),
      );
    }
  }
  Future<void> _addEvent(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final day = TextEditingController();
    final month = TextEditingController();
    final title = TextEditingController();
    final location = TextEditingController();
    final time = TextEditingController();

    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Termin erfassen'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: day,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Tag'),
              ),
              TextField(
                controller: month,
                decoration: const InputDecoration(labelText: 'Monat'),
              ),
              TextField(
                controller: title,
                decoration: const InputDecoration(labelText: 'Titel'),
              ),
              TextField(
                controller: location,
                decoration: const InputDecoration(labelText: 'Ort'),
              ),
              TextField(
                controller: time,
                decoration: const InputDecoration(labelText: 'Zeit'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Speichern'),
          ),
        ],
      ),
    );

    if (save == true &&
        day.text.trim().isNotEmpty &&
        month.text.trim().isNotEmpty &&
        title.text.trim().isNotEmpty) {
      store.addEvent(
        EventItem(
          day.text.trim(),
          month.text.trim().toUpperCase(),
          title.text.trim(),
          location.text.trim(),
          time.text.trim(),
        ),
      );
    }
  }

  Future<void> _editMember(
    BuildContext context, {
    int? index,
  }) async {
    final store = AppStoreScope.of(context);
    final existing = index == null ? null : store.members[index];

    final name = TextEditingController(text: existing?.name ?? '');
    final role = TextEditingController(text: existing?.role ?? 'Präsident');
    final since = TextEditingController(text: existing?.since ?? '');
    final partner = TextEditingController(text: existing?.partnerName ?? '');
    final phone = TextEditingController(text: existing?.phone ?? '');
    final email = TextEditingController(text: existing?.email ?? '');
    final address = TextEditingController(text: existing?.address ?? '');

    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(index == null ? 'Mitglied erfassen' : 'Mitglied bearbeiten'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              TextField(
                controller: role,
                decoration: const InputDecoration(labelText: 'Funktion'),
              ),
              TextField(
                controller: since,
                decoration: const InputDecoration(labelText: 'Mitglied seit'),
              ),
              TextField(
                controller: partner,
                decoration: const InputDecoration(
                  labelText: 'Partnerin / Partner',
                ),
              ),
              TextField(
                controller: phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Telefon'),
              ),
              TextField(
                controller: email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'E-Mail'),
              ),
              TextField(
                controller: address,
                decoration: const InputDecoration(
                  labelText: 'Wohnort / Adresse',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Speichern'),
          ),
        ],
      ),
    );

    if (save != true || name.text.trim().isEmpty) return;

    final item = MemberItem(
      name.text.trim(),
      role.text.trim().isEmpty ? 'Präsident' : role.text.trim(),
      since.text.trim(),
      partnerName: partner.text.trim(),
      phone: phone.text.trim(),
      email: email.text.trim(),
      address: address.text.trim(),
    );

    if (index == null) {
      store.addMember(item);
    } else {
      store.updateMember(index, item);
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    if (!store.canAdminister) {
      return const Scaffold(
        body: Center(
          child: Text('Keine Administrator-Berechtigung.'),
        ),
      );
    }

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Administration'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'News'),
              Tab(text: 'Termine'),
              Tab(text: 'Mitglieder'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _NewsAdminList(onAdd: () => _addNews(context)),
            _EventAdminList(onAdd: () => _addEvent(context)),
            _MemberAdminList(
              onAdd: () => _editMember(context),
              onEdit: (index) => _editMember(context, index: index),
            ),
          ],
        ),
      ),
    );
  }
}

class _NewsAdminList extends StatelessWidget {
  final VoidCallback onAdd;

  const _NewsAdminList({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FilledButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.add),
          label: const Text('Neue News'),
        ),
        const SizedBox(height: 12),
        for (var i = 0; i < store.news.length; i++)
          Card(
            child: ListTile(
              title: Text(store.news[i].title),
              subtitle: Text(store.news[i].date),
              trailing: IconButton(
                tooltip: 'Löschen',
                onPressed: () => store.deleteNews(i),
                icon: const Icon(Icons.delete_outline),
              ),
            ),
          ),
      ],
    );
  }
}

class _EventAdminList extends StatelessWidget {
  final VoidCallback onAdd;

  const _EventAdminList({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FilledButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.add),
          label: const Text('Termin erfassen'),
        ),
        const SizedBox(height: 12),
        for (var i = 0; i < store.events.length; i++)
          Card(
            child: ListTile(
              title: Text(store.events[i].title),
              subtitle: Text(
                '${store.events[i].day}. ${store.events[i].month} · '
                '${store.events[i].time}',
              ),
              trailing: IconButton(
                tooltip: 'Löschen',
                onPressed: () => store.deleteEvent(i),
                icon: const Icon(Icons.delete_outline),
              ),
            ),
          ),
      ],
    );
  }
}

class _MemberAdminList extends StatelessWidget {
  final VoidCallback onAdd;
  final ValueChanged<int> onEdit;

  const _MemberAdminList({
    required this.onAdd,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FilledButton.icon(
          onPressed: onAdd,
          icon: const Icon(Icons.person_add_alt_1),
          label: const Text('Mitglied erfassen'),
        ),
        const SizedBox(height: 12),
        for (var i = 0; i < store.members.length; i++)
          Card(
            child: ListTile(
              title: Text(store.members[i].name),
              subtitle: Text(
                store.members[i].partnerName.isEmpty
                    ? store.members[i].role
                    : '${store.members[i].role} · '
                        'Partner: ${store.members[i].partnerName}',
              ),
              onTap: () => onEdit(i),
              trailing: IconButton(
                tooltip: 'Löschen',
                onPressed: () => store.deleteMember(i),
                icon: const Icon(Icons.delete_outline),
              ),
            ),
          ),
      ],
    );
  }
}
