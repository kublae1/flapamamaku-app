import 'package:flutter/material.dart';
import '../data/app_store.dart';
import '../models/app_data.dart';

class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  Future<void> _addNews(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final title = TextEditingController();
    final text = TextEditingController();
    final date = TextEditingController(text: '23.09.2026');

    final save = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('News erfassen'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: date,
                decoration: const InputDecoration(labelText: 'Datum'),
              ),
              TextField(
                controller: title,
                decoration: const InputDecoration(labelText: 'Titel'),
              ),
              TextField(
                controller: text,
                minLines: 3,
                maxLines: 6,
                decoration: const InputDecoration(labelText: 'Text'),
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
        title.text.trim().isNotEmpty &&
        text.text.trim().isNotEmpty) {
      store.addNews(
        NewsItem(
          date.text.trim(),
          title.text.trim(),
          text.text.trim(),
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
            const _MemberAdminList(),
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
          label: const Text('News erfassen'),
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
  const _MemberAdminList();

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Card(
          child: ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Mitgliederverwaltung'),
            subtitle: Text(
              'Erfassen und Bearbeiten folgt im nächsten Schritt. '
              'Die Datenquelle ist bereits zentral vorbereitet.',
            ),
          ),
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < store.members.length; i++)
          Card(
            child: ListTile(
              title: Text(store.members[i].name),
              subtitle: Text(store.members[i].role),
            ),
          ),
      ],
    );
  }
}
