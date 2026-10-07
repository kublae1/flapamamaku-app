import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../data/message_api.dart';
import '../theme/flap_brand.dart';

class MessagesScreen extends StatefulWidget {
  const MessagesScreen({super.key});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  bool _loading = true;
  String? _error;
  List<ClubMessage> _messages = const [];

  MessageApi get _api => MessageApi(AppStoreScope.of(context).api);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loading && _messages.isEmpty && _error == null) {
      _load();
    }
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final values = await _api.fetchMessages();
      if (!mounted) return;
      setState(() => _messages = values);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _date(DateTime? value) {
    if (value == null) return '';
    final local = value.toLocal();
    final d = local.day.toString().padLeft(2, '0');
    final m = local.month.toString().padLeft(2, '0');
    final h = local.hour.toString().padLeft(2, '0');
    final min = local.minute.toString().padLeft(2, '0');
    return '$d.$m.${local.year} · $h:$min';
  }

  Future<void> _compose() async {
    final title = TextEditingController();
    final body = TextEditingController();
    var urgent = false;
    final send = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Mitteilung senden'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SegmentedButton<bool>(
                  segments: const [
                    ButtonSegment<bool>(
                      value: false,
                      icon: Icon(Icons.notifications_rounded),
                      label: Text('Vereinsmitteilung'),
                    ),
                    ButtonSegment<bool>(
                      value: true,
                      icon: Icon(Icons.priority_high_rounded),
                      label: Text('Dringend'),
                    ),
                  ],
                  selected: {urgent},
                  onSelectionChanged: (value) {
                    setDialogState(() => urgent = value.first);
                  },
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: title,
                  autofocus: true,
                  maxLength: 200,
                  decoration: const InputDecoration(labelText: 'Titel'),
                ),
                TextField(
                  controller: body,
                  minLines: 4,
                  maxLines: 8,
                  maxLength: 500,
                  decoration: const InputDecoration(labelText: 'Nachricht'),
                ),
                const SizedBox(height: 6),
                Text(
                  urgent
                      ? 'Dringend: maximale Benachrichtigungspriorität, Ton, Vibration und Heads-up (soweit Android-Einstellungen dies erlauben).'
                      : 'Vereinsmitteilung: hohe Priorität mit Ton, Vibration und Heads-up.',
                  style: TextStyle(
                    color: urgent ? Colors.redAccent : Colors.white60,
                    fontSize: 12,
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
            FilledButton.icon(
              onPressed: () {
                if (title.text.trim().isEmpty) return;
                Navigator.of(dialogContext).pop(true);
              },
              icon: const Icon(Icons.send_rounded),
              label: const Text('Senden'),
            ),
          ],
        ),
      ),
    );
    if (send != true) return;
    try {
      await _api.sendMessage(
        title: title.text.trim(),
        body: body.text.trim(),
        urgent: urgent,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            urgent
                ? 'Dringende Mitteilung wurde zur Zustellung eingereiht.'
                : 'Vereinsmitteilung wurde zur Zustellung eingereiht.',
          ),
        ),
      );
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Mitteilung konnte nicht gesendet werden: $error')),
      );
    }
  }

  Future<void> _open(ClubMessage message) async {
    if (!message.read) {
      try {
        await _api.markRead(message.id);
        if (mounted) {
          final index = _messages.indexWhere((item) => item.id == message.id);
          if (index >= 0) {
            final old = _messages[index];
            final updated = ClubMessage(
              id: old.id,
              kind: old.kind,
              title: old.title,
              body: old.body,
              route: old.route,
              createdAt: old.createdAt,
              read: true,
              urgent: old.urgent,
            );
            setState(() {
              final copy = [..._messages];
              copy[index] = updated;
              _messages = copy;
            });
          }
        }
      } catch (_) {}
    }
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            if (message.urgent) ...[
              const Icon(Icons.priority_high_rounded, color: Colors.redAccent),
              const SizedBox(width: 8),
            ],
            Expanded(child: Text(message.title)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _date(message.createdAt),
                style: const TextStyle(color: Colors.white54, fontSize: 12),
              ),
              if (message.body.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(message.body),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Schliessen'),
          ),
        ],
      ),
    );
  }

  Future<void> _markAll() async {
    try {
      await _api.markAllRead();
      if (!mounted) return;
      setState(() {
        _messages = _messages
            .map(
              (old) => ClubMessage(
                id: old.id,
                kind: old.kind,
                title: old.title,
                body: old.body,
                route: old.route,
                createdAt: old.createdAt,
                read: true,
                urgent: old.urgent,
              ),
            )
            .toList();
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Konnte nicht gespeichert werden: $error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final unread = _messages.where((item) => !item.read).length;
    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Mitteilungen',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          if (unread > 0)
            IconButton(
              tooltip: 'Alle gelesen',
              onPressed: _markAll,
              icon: const Icon(Icons.done_all_rounded),
            ),
          if (store.canManageUsers)
            IconButton(
              tooltip: 'Mitteilung senden',
              onPressed: _compose,
              icon: const Icon(Icons.add_alert_rounded),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading && _messages.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _messages.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(24),
                    children: [
                      const SizedBox(height: 70),
                      const Icon(
                        Icons.cloud_off_rounded,
                        color: Colors.white38,
                        size: 54,
                      ),
                      const SizedBox(height: 18),
                      Text(
                        _error!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white60),
                      ),
                    ],
                  )
                : _messages.isEmpty
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(24),
                        children: const [
                          SizedBox(height: 70),
                          Icon(
                            Icons.notifications_none_rounded,
                            color: Colors.white38,
                            size: 58,
                          ),
                          SizedBox(height: 18),
                          Text(
                            'Noch keine Mitteilungen vorhanden.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.white60),
                          ),
                        ],
                      )
                    : ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          final item = _messages[index];
                          return Card(
                            color: const Color(0xFF191B1E),
                            margin: const EdgeInsets.only(bottom: 10),
                            child: ListTile(
                              contentPadding: const EdgeInsets.fromLTRB(16, 10, 12, 10),
                              leading: Stack(
                                clipBehavior: Clip.none,
                                children: [
                                  CircleAvatar(
                                    backgroundColor: item.urgent
                                        ? Colors.red.shade800
                                        : Theme.of(context).colorScheme.primary,
                                    foregroundColor: Colors.white,
                                    child: Icon(
                                      item.urgent
                                          ? Icons.priority_high_rounded
                                          : Icons.notifications_rounded,
                                    ),
                                  ),
                                  if (!item.read)
                                    const Positioned(
                                      right: -2,
                                      top: -2,
                                      child: CircleAvatar(
                                        radius: 5,
                                        backgroundColor: FlapBrand.gold,
                                      ),
                                    ),
                                ],
                              ),
                              title: Text(
                                item.title,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: item.read
                                      ? FontWeight.w700
                                      : FontWeight.w900,
                                ),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (item.urgent)
                                    const Padding(
                                      padding: EdgeInsets.only(top: 4),
                                      child: Text(
                                        'DRINGENDE MITTEILUNG',
                                        style: TextStyle(
                                          color: Colors.redAccent,
                                          fontWeight: FontWeight.w900,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ),
                                  if (item.body.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Text(
                                        item.body,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(color: Colors.white60),
                                      ),
                                    ),
                                  Padding(
                                    padding: const EdgeInsets.only(top: 5),
                                    child: Text(
                                      _date(item.createdAt),
                                      style: const TextStyle(
                                        color: Colors.white38,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              trailing: const Icon(
                                Icons.chevron_right_rounded,
                                color: Colors.white38,
                              ),
                              onTap: () => _open(item),
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}
