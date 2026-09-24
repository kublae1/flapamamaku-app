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

  String _monthLabel(DateTime value) {
    const months = [
      'JAN', 'FEB', 'MÄR', 'APR', 'MAI', 'JUN',
      'JUL', 'AUG', 'SEP', 'OKT', 'NOV', 'DEZ',
    ];
    return months[value.month - 1];
  }

  Future<void> _editNews(
    BuildContext context, {
    int? index,
  }) async {
    final store = AppStoreScope.of(context);
    final now = DateTime.now();
    final existing = index == null ? null : store.news[index];

    final title = TextEditingController(text: existing?.title ?? '');
    final text = TextEditingController(text: existing?.text ?? '');
    final date = TextEditingController(
      text: existing?.date ?? _dateLabel(now),
    );
    String imageAsset = existing?.imageAsset ?? '';

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(index == null ? 'Neue News' : 'News bearbeiten'),
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

    if (save != true ||
        title.text.trim().isEmpty ||
        text.text.trim().isEmpty) {
      return;
    }

    final item = NewsItem(
      date.text.trim(),
      title.text.trim(),
      text.text.trim(),
      id: existing?.id,
      createdAt: existing?.createdAt ?? now.toIso8601String(),
      imageAsset: imageAsset,
      imageUrl: existing?.imageUrl ?? '',
    );

    if (index == null) {
      store.addNews(item);
    } else {
      store.updateNews(index, item);
    }
  }

  Future<void> _editEvent(
    BuildContext context, {
    int? index,
  }) async {
    final store = AppStoreScope.of(context);
    final existing = index == null ? null : store.events[index];

    final eventDate = TextEditingController(text: existing?.eventDate ?? '');
    final title = TextEditingController(text: existing?.title ?? '');
    final location = TextEditingController(text: existing?.location ?? '');
    final time = TextEditingController(text: existing?.time ?? '');

    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(index == null ? 'Termin erfassen' : 'Termin bearbeiten'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: eventDate,
                keyboardType: TextInputType.datetime,
                decoration: const InputDecoration(
                  labelText: 'Datum',
                  hintText: 'YYYY-MM-DD',
                ),
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

    final parsedDate = DateTime.tryParse(eventDate.text.trim());
    if (save != true || parsedDate == null || title.text.trim().isEmpty) {
      return;
    }

    final item = EventItem(
      parsedDate.day.toString().padLeft(2, '0'),
      _monthLabel(parsedDate),
      title.text.trim(),
      location.text.trim(),
      time.text.trim(),
      id: existing?.id,
      eventDate: eventDate.text.trim(),
    );

    if (index == null) {
      store.addEvent(item);
    } else {
      store.updateEvent(index, item);
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
    final mobile = TextEditingController(text: existing?.phoneMobile ?? '');
    final privatePhone = TextEditingController(text: existing?.phonePrivate ?? '');
    final workPhone = TextEditingController(text: existing?.phoneWork ?? '');
    final email = TextEditingController(text: existing?.email ?? '');
    final address = TextEditingController(text: existing?.address ?? '');
    final occupation = TextEditingController(text: existing?.occupation ?? '');
    final employer = TextEditingController(text: existing?.employer ?? '');

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
                controller: mobile,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Mobil'),
              ),
              TextField(
                controller: privatePhone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Telefon privat'),
              ),
              TextField(
                controller: workPhone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Telefon Arbeit'),
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
              TextField(
                controller: occupation,
                decoration: const InputDecoration(labelText: 'Beruf'),
              ),
              TextField(
                controller: employer,
                decoration: const InputDecoration(labelText: 'Arbeitgeber'),
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
      id: existing?.id,
      partnerName: partner.text.trim(),
      phoneMobile: mobile.text.trim(),
      phonePrivate: privatePhone.text.trim(),
      phoneWork: workPhone.text.trim(),
      email: email.text.trim(),
      address: address.text.trim(),
      occupation: occupation.text.trim(),
      employer: employer.text.trim(),
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

    final tabs = <Tab>[];
    final views = <Widget>[];

    if (store.canNews) {
      tabs.add(const Tab(text: 'News'));
      views.add(
        _NewsAdminList(
          onAdd: () => _editNews(context),
          onEdit: (index) => _editNews(context, index: index),
        ),
      );
    }
    if (store.canEvents) {
      tabs.add(const Tab(text: 'Termine'));
      views.add(
        _EventAdminList(
          onAdd: () => _editEvent(context),
          onEdit: (index) => _editEvent(context, index: index),
        ),
      );
    }
    if (store.canMembers) {
      tabs.add(const Tab(text: 'Mitglieder'));
      views.add(
        _MemberAdminList(
          onAdd: () => _editMember(context),
          onEdit: (index) => _editMember(context, index: index),
        ),
      );
    }

    if (tabs.isEmpty) {
      return const Scaffold(
        body: Center(
          child: Text('Keine Verwaltungsberechtigung vorhanden.'),
        ),
      );
    }

    return DefaultTabController(
      length: tabs.length,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Administration'),
          bottom: TabBar(tabs: tabs),
        ),
        body: TabBarView(children: views),
      ),
    );
  }
}

class _NewsAdminList extends StatelessWidget {
  final VoidCallback onAdd;
  final ValueChanged<int> onEdit;

  const _NewsAdminList({
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
          icon: const Icon(Icons.add),
          label: const Text('Neue News'),
        ),
        const SizedBox(height: 12),
        for (var i = 0; i < store.news.length; i++)
          Card(
            child: ListTile(
              title: Text(store.news[i].title),
              subtitle: Text(store.news[i].date),
              onTap: () => onEdit(i),
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
  final ValueChanged<int> onEdit;

  const _EventAdminList({
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
              onTap: () => onEdit(i),
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
                store.members[i].occupation.isEmpty
                    ? store.members[i].role
                    : '${store.members[i].role} · ${store.members[i].occupation}',
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
