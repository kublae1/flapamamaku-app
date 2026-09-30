import 'package:flutter/material.dart';
import '../data/app_store.dart';
import '../theme/flap_brand.dart';
import 'content_detail_screens.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  final Set<int> calendarEvents = {};

  Future<bool?> _ask(
    BuildContext context, {
    required String title,
    required String question,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(question),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Nein'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Ja'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteEvent(
    BuildContext context,
    int index,
  ) async {
    final store = AppStoreScope.of(context);
    final event = store.events[index];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Termin löschen?'),
        content: Text('„${event.title}“ wird endgültig gelöscht.'),
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
    );
    if (confirmed != true) return;

    try {
      await store.deleteEvent(index);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Termin gelöscht.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Termin konnte nicht gelöscht werden.')),
        );
      }
    }
  }

  Future<bool> _handleSwipe(
    BuildContext context,
    int index,
    DismissDirection direction,
  ) async {
    final store = AppStoreScope.of(context);
    final event = store.events[index];

    if (direction == DismissDirection.endToStart) {
      final result = await _ask(
        context,
        title: 'Anmelden',
        question: 'Für „${event.title}“ anmelden?',
      );
      if (result != null && event.id != null) {
        await store.setEventRegistration(event, result);
      }
      return false;
    }

    if (direction == DismissDirection.startToEnd) {
      final result = await _ask(
        context,
        title: 'Kalender',
        question: '„${event.title}“ in den Kalender eintragen?',
      );
      if (result == true && mounted) {
        setState(() => calendarEvents.add(index));
      } else if (result == false && mounted) {
        setState(() => calendarEvents.remove(index));
      }
      return false;
    }

    return false;
  }

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final events = store.events;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(title: const Text('Termine')),
      body: RefreshIndicator(
        onRefresh: store.refreshFromServer,
        child: ListView.builder(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
        itemCount: events.length,
        itemBuilder: (_, i) {
          final e = events[i];
          final isRegistered = e.registeredByMe;
          final isInCalendar = calendarEvents.contains(i);

          return Dismissible(
            key: ValueKey('event-$i-${e.title}'),
            direction: DismissDirection.horizontal,
            confirmDismiss: (direction) => _handleSwipe(
              context,
              i,
              direction,
            ),
            background: Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              alignment: Alignment.centerLeft,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.calendar_month_outlined),
                  SizedBox(width: 8),
                  Text(
                    'Kalender',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
            secondaryBackground: Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              alignment: Alignment.centerRight,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.secondaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Anmelden',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.how_to_reg_outlined),
                ],
              ),
            ),
            child: Card(
              color: const Color(0xFF191B1E),
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: Container(
                  width: 92,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: FlapBrand.burgundy,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    e.displayDate,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                title: Text(
                  e.title,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${e.displayDate}\n${e.location}\n${e.time}', style: const TextStyle(color: Colors.white70)),
                    const SizedBox(height: 4),
                    Text(
                      '${e.registrationCount} angemeldet',
                      style: const TextStyle(color: FlapBrand.gold, fontWeight: FontWeight.w700),
                    ),
                    if (isRegistered || isInCalendar) ...[
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        runSpacing: 4,
                        children: [
                          if (isRegistered)
                            const Chip(
                              avatar: Icon(Icons.check_circle_outline, size: 18),
                              label: Text('Angemeldet'),
                            ),
                          if (isInCalendar)
                            const Chip(
                              avatar: Icon(Icons.calendar_month_outlined, size: 18),
                              label: Text('Im Kalender'),
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
                isThreeLine: true,
                trailing: store.canEvents
                    ? IconButton(
                        tooltip: 'Termin löschen',
                        onPressed: () => _deleteEvent(context, i),
                        icon: const Icon(Icons.delete_outline),
                      )
                    : const Icon(Icons.chevron_right, color: Colors.white70),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => EventDetailScreen(event: e),
                  ),
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
