import 'package:flutter/material.dart';
import '../models/app_data.dart';
import 'content_detail_screens.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  final Set<int> registeredEvents = {};
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

  Future<bool> _handleSwipe(
    BuildContext context,
    int index,
    DismissDirection direction,
  ) async {
    final event = eventItems[index];

    if (direction == DismissDirection.endToStart) {
      final result = await _ask(
        context,
        title: 'Anmelden',
        question: 'Für „${event.title}“ anmelden?',
      );
      if (result == true && mounted) {
        setState(() => registeredEvents.add(index));
      } else if (result == false && mounted) {
        setState(() => registeredEvents.remove(index));
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
    return Scaffold(
      appBar: AppBar(title: const Text('Termine')),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: eventItems.length,
        itemBuilder: (_, i) {
          final e = eventItems[i];
          final isRegistered = registeredEvents.contains(i);
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
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: Container(
                  width: 54,
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        e.day,
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(e.month),
                    ],
                  ),
                ),
                title: Text(
                  e.title,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${e.location}\n${e.time}'),
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
                trailing: const Icon(Icons.chevron_right),
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
    );
  }
}
