import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_store.dart';
import '../models/app_data.dart';
import '../theme/flap_brand.dart';
import 'flap_image_viewer_screen.dart';

class NewsDetailScreen extends StatelessWidget {
  final NewsItem item;

  const NewsDetailScreen({required this.item, super.key});

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);
    final hasImage = item.imageUrl.isNotEmpty || item.imageAsset.isNotEmpty;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text('News', style: TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          if (hasImage)
            GestureDetector(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => FlapImageViewerScreen(
                    title: item.title,
                    imageUrl: item.imageUrl,
                    imageAsset: item.imageAsset,
                  ),
                ),
              ),
              child: Stack(
                children: [
                  AspectRatio(
                    aspectRatio: 4 / 3,
                    child: item.imageUrl.isNotEmpty
                        ? Image.network(
                            item.imageUrl,
                            headers: store.api.authHeaders,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const _ImageError(),
                          )
                        : Image.asset(
                            item.imageAsset,
                            width: double.infinity,
                            fit: BoxFit.cover,
                          ),
                  ),
                  const Positioned(
                    right: 14,
                    bottom: 14,
                    child: _ZoomBadge(),
                  ),
                ],
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 34),
            child: Column(
              children: [
                Text(
                  item.title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  item.date,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: FlapBrand.gold,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  item.text,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 16,
                    height: 1.55,
                  ),
                ),
              ],
            ),
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
  bool _loadedRegistrations = false;
  bool _loadingRegistrations = false;
  List<String> registrations = [];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loadedRegistrations) return;
    _loadedRegistrations = true;
    registered = widget.event.registeredByMe;
    _loadRegistrations();
  }

  Future<void> _loadRegistrations() async {
    if (widget.event.id == null || _loadingRegistrations) return;
    _loadingRegistrations = true;
    try {
      final names = await AppStoreScope.of(context)
          .api
          .fetchEventRegistrations(widget.event.id!);
      if (mounted) setState(() => registrations = names);
    } finally {
      _loadingRegistrations = false;
    }
  }

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
    final store = AppStoreScope.of(context);
    final result = await _ask(
      'Anmelden',
      'Für „${widget.event.title}“ anmelden?',
    );
    if (result != null && widget.event.id != null) {
      await store.setEventRegistration(widget.event, result);
      if (mounted) {
        setState(() => registered = result);
        await _loadRegistrations();
      }
    }
  }

  Future<void> _addToCalendar() async {
    final result = await _ask(
      'Kalender',
      '„${widget.event.title}“ in den Kalender eintragen?',
    );
    if (result != null && mounted) setState(() => inCalendar = result);
  }

  @override
  Widget build(BuildContext context) {
    final event = widget.event;

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text('Termin', style: TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(20, 30, 20, 28),
            color: FlapBrand.burgundy,
            child: Column(
              children: [
                const Icon(
                  Icons.calendar_month_rounded,
                  color: Colors.white,
                  size: 52,
                ),
                const SizedBox(height: 12),
                Text(
                  event.displayDate,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 22, 18, 34),
            child: Column(
              children: [
                Text(
                  event.title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 18),
                _DarkPanel(
                  child: Column(
                    children: [
                      _DarkInfoRow(
                        icon: Icons.calendar_month_outlined,
                        text: event.displayDate,
                      ),
                      const _DarkDivider(),
                      _DarkInfoRow(
                        icon: Icons.schedule_outlined,
                        text: event.time,
                      ),
                      const _DarkDivider(),
                      _DarkInfoRow(
                        icon: Icons.location_on_outlined,
                        text: event.location,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: FlapBrand.burgundy,
                          foregroundColor: Colors.white,
                          minimumSize: const Size.fromHeight(52),
                        ),
                        onPressed: _register,
                        icon: Icon(
                          registered
                              ? Icons.check_circle
                              : Icons.how_to_reg_outlined,
                        ),
                        label: Text(registered ? 'Angemeldet' : 'Anmelden'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white,
                          side: const BorderSide(color: FlapBrand.gold),
                          minimumSize: const Size.fromHeight(52),
                        ),
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
                const SizedBox(height: 16),
                _DarkPanel(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Angemeldete Mitglieder (${registrations.length})',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (registrations.isEmpty)
                          const Text(
                            'Noch niemand angemeldet.',
                            style: TextStyle(color: Colors.white60),
                          )
                        else
                          ...registrations.map(
                            (name) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.person_outline,
                                    color: FlapBrand.gold,
                                    size: 20,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      name,
                                      style: const TextStyle(color: Colors.white70),
                                    ),
                                  ),
                                ],
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
        ],
      ),
    );
  }
}

class MemberDetailScreen extends StatelessWidget {
  final MemberItem member;

  const MemberDetailScreen({required this.member, super.key});

  Future<void> _launch(BuildContext context, Uri uri) async {
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Aktion konnte nicht geöffnet werden.')),
      );
    }
  }

  Future<void> _call(BuildContext context, String number) async {
    if (number.isNotEmpty) await _launch(context, Uri(scheme: 'tel', path: number));
  }

  Future<void> _mail(BuildContext context) async {
    if (member.email.isNotEmpty) {
      await _launch(context, Uri(scheme: 'mailto', path: member.email));
    }
  }

  Future<void> _maps(BuildContext context) async {
    if (member.address.isEmpty) return;
    await _launch(
      context,
      Uri.https('www.google.com', '/maps/search/', {
        'api': '1',
        'query': member.address,
      }),
    );
  }

  Future<void> _openEmployerWebsite(BuildContext context) async {
    final value = member.employerUrl.trim();
    if (value.isEmpty) return;
    final normalized = value.startsWith('http://') || value.startsWith('https://')
        ? value
        : 'https://$value';
    final uri = Uri.tryParse(normalized);
    if (uri != null) await _launch(context, uri);
  }

  String _value(String value) => value.isEmpty ? 'Nicht hinterlegt' : value;

  @override
  Widget build(BuildContext context) {
    final headers = AppStoreScope.of(context).api.authHeaders;

    Widget phoneTile(String label, String number, IconData icon) {
      return _DarkInfoTile(
        icon: icon,
        title: label,
        value: _value(number),
        actionIcon: Icons.call_rounded,
        onAction: number.isEmpty ? null : () => _call(context, number),
      );
    }

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text('Mitglied', style: TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          if (member.photoUrl.isNotEmpty)
            GestureDetector(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => FlapImageViewerScreen(
                    title: member.name,
                    imageUrl: member.photoUrl,
                  ),
                ),
              ),
              child: Stack(
                children: [
                  AspectRatio(
                    aspectRatio: 4 / 3,
                    child: Image.network(
                      member.photoUrl,
                      headers: headers,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const _ImageError(),
                    ),
                  ),
                  const Positioned(
                    right: 14,
                    bottom: 14,
                    child: _ZoomBadge(),
                  ),
                ],
              ),
            )
          else
            Container(
              height: 230,
              color: FlapBrand.burgundy,
              alignment: Alignment.center,
              child: Text(
                member.name.isEmpty ? '?' : member.name.characters.first,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 76,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 20, 18, 34),
            child: Column(
              children: [
                Text(
                  member.name,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 25,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  member.role,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: FlapBrand.gold,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (member.since.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    member.since,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white60),
                  ),
                ],
                const SizedBox(height: 22),
                _DarkPanel(
                  child: Column(
                    children: [
                      _DarkInfoTile(
                        icon: Icons.favorite_outline,
                        title: 'Partnerin / Partner',
                        value: _value(member.partnerName),
                      ),
                      const _DarkDivider(),
                      phoneTile('Mobil', member.phoneMobile, Icons.smartphone),
                      const _DarkDivider(),
                      phoneTile(
                        'Telefon privat',
                        member.phonePrivate,
                        Icons.phone_outlined,
                      ),
                      const _DarkDivider(),
                      phoneTile(
                        'Telefon Arbeit',
                        member.phoneWork,
                        Icons.business_center_outlined,
                      ),
                      const _DarkDivider(),
                      _DarkInfoTile(
                        icon: Icons.mail_outline,
                        title: 'E-Mail',
                        value: _value(member.email),
                        actionIcon: Icons.send_outlined,
                        onAction: member.email.isEmpty ? null : () => _mail(context),
                      ),
                      const _DarkDivider(),
                      _DarkInfoTile(
                        icon: Icons.home_outlined,
                        title: 'Wohnort',
                        value: _value(member.address),
                        actionIcon: Icons.map_outlined,
                        onAction: member.address.isEmpty ? null : () => _maps(context),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                _DarkPanel(
                  child: Column(
                    children: [
                      _DarkInfoTile(
                        icon: Icons.badge_outlined,
                        title: 'Beruf',
                        value: _value(member.occupation),
                      ),
                      const _DarkDivider(),
                      _DarkInfoTile(
                        icon: Icons.business_outlined,
                        title: 'Arbeitgeber',
                        value: _value(member.employer),
                        actionIcon: Icons.open_in_new_rounded,
                        onAction: member.employerUrl.isEmpty
                            ? null
                            : () => _openEmployerWebsite(context),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DarkPanel extends StatelessWidget {
  final Widget child;

  const _DarkPanel({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0x18FFFFFF)),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }
}

class _DarkInfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _DarkInfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(icon, color: FlapBrand.gold),
          const SizedBox(width: 13),
          Expanded(
            child: Text(
              text.isEmpty ? 'Nicht hinterlegt' : text,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DarkInfoTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;
  final IconData? actionIcon;
  final VoidCallback? onAction;

  const _DarkInfoTile({
    required this.icon,
    required this.title,
    required this.value,
    this.actionIcon,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: FlapBrand.gold),
      title: Text(
        title,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
      ),
      subtitle: Text(value, style: const TextStyle(color: Colors.white60)),
      trailing: actionIcon == null
          ? null
          : IconButton(
              onPressed: onAction,
              color: onAction == null ? Colors.white24 : FlapBrand.gold,
              icon: Icon(actionIcon),
            ),
      onTap: onAction,
    );
  }
}

class _DarkDivider extends StatelessWidget {
  const _DarkDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(height: 1, color: Color(0x22FFFFFF));
  }
}

class _ZoomBadge extends StatelessWidget {
  const _ZoomBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: const BoxDecoration(
        color: Color(0xCC000000),
        shape: BoxShape.circle,
      ),
      child: const Icon(Icons.zoom_in_rounded, color: Colors.white, size: 22),
    );
  }
}

class _ImageError extends StatelessWidget {
  const _ImageError();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF24272B),
      alignment: Alignment.center,
      child: const Icon(
        Icons.broken_image_outlined,
        color: Colors.white54,
        size: 50,
      ),
    );
  }
}
