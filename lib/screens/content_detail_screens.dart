import 'package:flutter/material.dart';
import '../models/app_data.dart';

class NewsDetailScreen extends StatelessWidget {
  final NewsItem item;

  const NewsDetailScreen({required this.item, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('News')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            item.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            item.date,
            style: TextStyle(color: Theme.of(context).colorScheme.primary),
          ),
          const SizedBox(height: 20),
          Text(
            item.text,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

class EventDetailScreen extends StatefulWidget {
  final EventItem event;

  const EventDetailScreen({required this.event, super.key});

  @override
  State<EventDetailScreen> createState() => _EventDetailScreenState();
}

class _EventDetailScreenState extends State<EventDetailScreen> {
  bool registered = false;
  bool inCalendar = false;

  Future<bool?> _ask(String title, String question) {
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

  Future<void> _register() async {
    final result = await _ask(
      'Anmelden',
      'Für „${widget.event.title}“ anmelden?',
    );
    if (result != null && mounted) {
      setState(() => registered = result);
    }
  }

  Future<void> _addToCalendar() async {
    final result = await _ask(
      'Kalender',
      '„${widget.event.title}“ in den Kalender eintragen?',
    );
    if (result != null && mounted) {
      setState(() => inCalendar = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final event = widget.event;

    return Scaffold(
      appBar: AppBar(title: const Text('Termin')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            event.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 20),
          _InfoRow(
            icon: Icons.calendar_month_outlined,
            text: '${event.day}. ${event.month}',
          ),
          _InfoRow(icon: Icons.schedule_outlined, text: event.time),
          _InfoRow(icon: Icons.location_on_outlined, text: event.location),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _register,
                  icon: Icon(
                    registered
                        ? Icons.check_circle
                        : Icons.how_to_reg_outlined,
                  ),
                  label: Text(registered ? 'Angemeldet' : 'Anmelden'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _addToCalendar,
                  icon: Icon(
                    inCalendar
                        ? Icons.event_available
                        : Icons.calendar_month_outlined,
                  ),
                  label: Text(inCalendar ? 'Im Kalender' : 'Kalender'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Weitere Angaben wie Treffpunkt, Beschreibung und Dokumente können später vom Administrator gepflegt werden.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class MemberDetailScreen extends StatelessWidget {
  final MemberItem member;

  const MemberDetailScreen({required this.member, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mitglied')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Center(
            child: CircleAvatar(
              radius: 44,
              child: Text(
                member.name.characters.first,
                style: const TextStyle(
                  fontSize: 30,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            member.name,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            member.role,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            member.since,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          const Card(
            child: ListTile(
              leading: Icon(Icons.badge_outlined),
              title: Text('Mitgliederprofil'),
              subtitle: Text(
                'Kontaktdaten, Foto und weitere Angaben werden später administrierbar.',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SimpleSectionScreen extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;

  const SimpleSectionScreen({
    required this.title,
    required this.description,
    required this.icon,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Icon(
            icon,
            size: 64,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(height: 20),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 12),
          Text(
            description,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}
