import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';

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

  void _message(BuildContext context, String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<bool> _confirmDelete(BuildContext context, String label) async {
    return await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const Text('Wirklich löschen?'),
            content: Text('$label wird endgültig vom Server gelöscht.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: const Text('Abbrechen'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                icon: const Icon(Icons.delete_outline),
                label: const Text('Löschen'),
              ),
            ],
          ),
        ) ??
        false;
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

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
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
                decoration: const InputDecoration(
                  labelText: 'Datum',
                  hintText: 'z. B. 03.10.2026',
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Newsbilder werden zentral im PC-Admin verwaltet. '
                'Die App verwendet keine fest eingebauten Vereinsbilder mehr.',
                style: TextStyle(color: Colors.white60, fontSize: 13),
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
    );

    if (save != true) return;
    if (title.text.trim().isEmpty || text.text.trim().isEmpty) {
      if (context.mounted) {
        _message(context, 'Bitte Titel und Text vollständig eingeben.');
      }
      return;
    }

    final item = NewsItem(
      date.text.trim(),
      title.text.trim(),
      text.text.trim(),
      id: existing?.id,
      createdAt: existing?.createdAt ?? now.toIso8601String(),
      imageUrl: existing?.imageUrl ?? '',
    );

    try {
      if (index == null) {
        await store.addNews(item);
      } else {
        await store.updateNews(index, item);
      }
      if (context.mounted) {
        _message(
          context,
          index == null ? 'News gespeichert.' : 'News aktualisiert.',
        );
      }
    } catch (error) {
      if (context.mounted) {
        _message(
          context,
          store.userMessageForError(
            error,
            fallback: 'News konnten nicht gespeichert werden.',
          ),
        );
      }
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
      builder: (dialogContext) => AlertDialog(
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
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Speichern'),
          ),
        ],
      ),
    );

    if (save != true) return;
    final parsedDate = DateTime.tryParse(eventDate.text.trim());
    if (parsedDate == null || title.text.trim().isEmpty) {
      if (context.mounted) {
        _message(context, 'Bitte ein gültiges Datum (YYYY-MM-DD) und einen Titel eingeben.');
      }
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

    try {
      if (index == null) {
        await store.addEvent(item);
      } else {
        await store.updateEvent(index, item);
      }
      if (context.mounted) {
        _message(
          context,
          index == null ? 'Termin gespeichert.' : 'Termin aktualisiert.',
        );
      }
    } catch (error) {
      if (context.mounted) {
        _message(
          context,
          store.userMessageForError(
            error,
            fallback: 'Termin konnte nicht gespeichert werden.',
          ),
        );
      }
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
    final employerUrl = TextEditingController(text: existing?.employerUrl ?? '');

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
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
              TextField(
                controller: employerUrl,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  labelText: 'Webseite Arbeitgeber',
                  hintText: 'https://...',
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
    );

    if (save != true) return;
    if (name.text.trim().isEmpty) {
      if (context.mounted) _message(context, 'Bitte einen Namen eingeben.');
      return;
    }

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
      employerUrl: employerUrl.text.trim(),
      photoUrl: existing?.photoUrl ?? '',
    );

    try {
      if (index == null) {
        await store.addMember(item);
      } else {
        await store.updateMember(index, item);
      }
      if (context.mounted) {
        _message(
          context,
          index == null ? 'Mitglied gespeichert.' : 'Mitglied aktualisiert.',
        );
      }
    } catch (error) {
      if (context.mounted) {
        _message(
          context,
          store.userMessageForError(
            error,
            fallback: 'Mitglied konnte nicht gespeichert werden.',
          ),
        );
      }
    }
  }

  Future<void> _deleteNews(BuildContext context, int index) async {
    final store = AppStoreScope.of(context);
    final item = store.news[index];
    if (!await _confirmDelete(context, 'News „${item.title}“')) return;
    try {
      await store.deleteNews(index);
      if (context.mounted) _message(context, 'News gelöscht.');
    } catch (error) {
      if (context.mounted) {
        _message(context, store.userMessageForError(error, fallback: 'News konnten nicht gelöscht werden.'));
      }
    }
  }

  Future<void> _deleteEvent(BuildContext context, int index) async {
    final store = AppStoreScope.of(context);
    final item = store.events[index];
    if (!await _confirmDelete(context, 'Termin „${item.title}“')) return;
    try {
      await store.deleteEvent(index);
      if (context.mounted) _message(context, 'Termin gelöscht.');
    } catch (error) {
      if (context.mounted) {
        _message(context, store.userMessageForError(error, fallback: 'Termin konnte nicht gelöscht werden.'));
      }
    }
  }

  Future<void> _deleteMember(BuildContext context, int index) async {
    final store = AppStoreScope.of(context);
    final item = store.members[index];
    if (!await _confirmDelete(context, 'Mitglied „${item.name}“')) return;
    try {
      await store.deleteMember(index);
      if (context.mounted) _message(context, 'Mitglied gelöscht.');
    } catch (error) {
      if (context.mounted) {
        _message(context, store.userMessageForError(error, fallback: 'Mitglied konnte nicht gelöscht werden.'));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    if (!store.canAdminister) {
      return const Scaffold(
        backgroundColor: FlapBrand.charcoal,
        body: Center(
          child: Text(
            'Keine Administrator-Berechtigung.',
            style: TextStyle(color: Colors.white70),
          ),
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
          onDelete: (index) => _deleteNews(context, index),
        ),
      );
    }
    if (store.canEvents) {
      tabs.add(const Tab(text: 'Termine'));
      views.add(
        _EventAdminList(
          onAdd: () => _editEvent(context),
          onEdit: (index) => _editEvent(context, index: index),
          onDelete: (index) => _deleteEvent(context, index),
        ),
      );
    }
    if (store.canMembers) {
      tabs.add(const Tab(text: 'Mitglieder'));
      views.add(
        _MemberAdminList(
          onAdd: () => _editMember(context),
          onEdit: (index) => _editMember(context, index: index),
          onDelete: (index) => _deleteMember(context, index),
        ),
      );
    }

    if (tabs.isEmpty) {
      return const Scaffold(
        backgroundColor: FlapBrand.charcoal,
        body: Center(
          child: Text(
            'Keine Verwaltungsberechtigung vorhanden.',
            style: TextStyle(color: Colors.white70),
          ),
        ),
      );
    }

    return DefaultTabController(
      length: tabs.length,
      child: Scaffold(
        backgroundColor: FlapBrand.charcoal,
        appBar: AppBar(
          title: const Text(
            'Administration',
            style: TextStyle(fontWeight: FontWeight.w900),
          ),
          actions: [
            IconButton(
              tooltip: 'Aktualisieren',
              onPressed: store.isSyncing ? null : store.refreshFromServer,
              icon: store.isSyncing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.refresh),
            ),
          ],
          bottom: TabBar(
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white60,
            indicatorColor: FlapBrand.gold,
            indicatorWeight: 3,
            tabs: tabs,
          ),
        ),
        body: Column(
          children: [
            if (store.syncError != null && store.syncError!.trim().isNotEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                color: const Color(0xFF4A1D20),
                child: Text(
                  store.syncError!,
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            Expanded(child: TabBarView(children: views)),
          ],
        ),
      ),
    );
  }
}

class _NewsAdminList extends StatelessWidget {
  final VoidCallback onAdd;
  final ValueChanged<int> onEdit;
  final ValueChanged<int> onDelete;

  const _NewsAdminList({
    required this.onAdd,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return RefreshIndicator(
      onRefresh: store.refreshFromServer,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: FlapBrand.burgundy,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(50),
            ),
            onPressed: onAdd,
            icon: const Icon(Icons.add),
            label: const Text('Neue News'),
          ),
          const SizedBox(height: 12),
          if (store.news.isEmpty)
            const _AdminEmptyState('Noch keine News vorhanden.'),
          for (var i = 0; i < store.news.length; i++)
            Card(
              color: const Color(0xFF191B1E),
              child: ListTile(
                title: Text(
                  store.news[i].title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                subtitle: Text(
                  store.news[i].date,
                  style: const TextStyle(color: Colors.white60),
                ),
                onTap: () => onEdit(i),
                trailing: IconButton(
                  tooltip: 'Löschen',
                  onPressed: () => onDelete(i),
                  icon: const Icon(Icons.delete_outline, color: Colors.white54),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _EventAdminList extends StatelessWidget {
  final VoidCallback onAdd;
  final ValueChanged<int> onEdit;
  final ValueChanged<int> onDelete;

  const _EventAdminList({
    required this.onAdd,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return RefreshIndicator(
      onRefresh: store.refreshFromServer,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: FlapBrand.burgundy,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(50),
            ),
            onPressed: onAdd,
            icon: const Icon(Icons.add),
            label: const Text('Termin erfassen'),
          ),
          const SizedBox(height: 12),
          if (store.events.isEmpty)
            const _AdminEmptyState('Noch keine Termine vorhanden.'),
          for (var i = 0; i < store.events.length; i++)
            Card(
              color: const Color(0xFF191B1E),
              child: ListTile(
                title: Text(
                  store.events[i].title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                subtitle: Text(
                  '${store.events[i].displayDate} · ${store.events[i].time}',
                  style: const TextStyle(color: Colors.white60),
                ),
                onTap: () => onEdit(i),
                trailing: IconButton(
                  tooltip: 'Löschen',
                  onPressed: () => onDelete(i),
                  icon: const Icon(Icons.delete_outline, color: Colors.white54),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _MemberAdminList extends StatelessWidget {
  final VoidCallback onAdd;
  final ValueChanged<int> onEdit;
  final ValueChanged<int> onDelete;

  const _MemberAdminList({
    required this.onAdd,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return RefreshIndicator(
      onRefresh: store.refreshFromServer,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: FlapBrand.burgundy,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(50),
            ),
            onPressed: onAdd,
            icon: const Icon(Icons.person_add_alt_1),
            label: const Text('Mitglied erfassen'),
          ),
          const SizedBox(height: 12),
          if (store.members.isEmpty)
            const _AdminEmptyState('Noch keine Mitglieder vorhanden.'),
          for (var i = 0; i < store.members.length; i++)
            Card(
              color: const Color(0xFF191B1E),
              child: ListTile(
                title: Text(
                  store.members[i].name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                subtitle: Text(
                  store.members[i].occupation.isEmpty
                      ? store.members[i].role
                      : '${store.members[i].role} · ${store.members[i].occupation}',
                  style: const TextStyle(color: Colors.white60),
                ),
                onTap: () => onEdit(i),
                trailing: IconButton(
                  tooltip: 'Löschen',
                  onPressed: () => onDelete(i),
                  icon: const Icon(Icons.delete_outline, color: Colors.white54),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _AdminEmptyState extends StatelessWidget {
  final String text;

  const _AdminEmptyState(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0x18FFFFFF)),
      ),
      child: Text(text, style: const TextStyle(color: Colors.white60)),
    );
  }
}
