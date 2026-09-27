import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
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

class MemberDetailScreen extends StatefulWidget {
  final MemberItem member;

  const MemberDetailScreen({required this.member, super.key});

  @override
  State<MemberDetailScreen> createState() => _MemberDetailScreenState();
}

class _MemberDetailScreenState extends State<MemberDetailScreen> {
  late MemberItem member;

  @override
  void initState() {
    super.initState();
    member = widget.member;
  }

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

  Future<void> _message(BuildContext context) async {
    final number = member.phoneMobile.trim();
    if (number.isNotEmpty) {
      await _launch(context, Uri(scheme: 'sms', path: number));
    }
  }

  Future<void> _openFlapChat(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final link = store
        .contentFor('whatsapp')
        .map((item) => item.linkUrl.trim())
        .firstWhere((value) => value.isNotEmpty, orElse: () => '');

    if (link.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('FLAPAMAMAKU Chat-Link ist noch nicht hinterlegt.'),
        ),
      );
      return;
    }

    final uri = Uri.tryParse(link);
    if (uri == null || !(uri.scheme == 'https' || uri.scheme == 'http')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('FLAPAMAMAKU Chat-Link ist ungültig.')),
      );
      return;
    }

    await _launch(context, uri);
  }

  Future<void> _editOwnProfile(BuildContext context) async {
    final store = AppStoreScope.of(context);
    final partner = TextEditingController(text: member.partnerName);
    final mobile = TextEditingController(text: member.phoneMobile);
    final privatePhone = TextEditingController(text: member.phonePrivate);
    final workPhone = TextEditingController(text: member.phoneWork);
    final email = TextEditingController(text: member.email);
    final address = TextEditingController(text: member.address);
    final occupation = TextEditingController(text: member.occupation);
    final employer = TextEditingController(text: member.employer);
    final employerUrl = TextEditingController(text: member.employerUrl);
    final engagement = TextEditingController(text: member.engagement);
    XFile? selectedPhoto;

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: FlapBrand.charcoal,
      builder: (sheetContext) {
        bool saving = false;
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            Future<void> save() async {
              if (saving) return;
              setSheetState(() => saving = true);
              try {
                final updated = MemberItem(
                  member.name,
                  member.role,
                  member.since,
                  id: member.id,
                  birthDate: member.birthDate,
                  status: member.status,
                  memberGroup: member.memberGroup,
                  engagement: engagement.text.trim(),
                  sortOrder: member.sortOrder,
                  filterIds: member.filterIds,
                  partnerName: partner.text.trim(),
                  phoneMobile: mobile.text.trim(),
                  phonePrivate: privatePhone.text.trim(),
                  phoneWork: workPhone.text.trim(),
                  email: email.text.trim(),
                  address: address.text.trim(),
                  occupation: occupation.text.trim(),
                  employer: employer.text.trim(),
                  employerUrl: employerUrl.text.trim(),
                  photoUrl: member.photoUrl,
                );
                var result = await store.api.updateOwnMember(updated);
                if (selectedPhoto != null) {
                  final bytes = await selectedPhoto!.readAsBytes();
                  result = await store.api.uploadOwnMemberPhoto(
                    bytes: bytes,
                    filename: selectedPhoto!.name,
                  );
                }
                await store.refreshFromServer();
                if (!mounted) return;
                setState(() => member = result);
                if (sheetContext.mounted) Navigator.of(sheetContext).pop(true);
              } catch (_) {
                if (sheetContext.mounted) {
                  ScaffoldMessenger.of(sheetContext).showSnackBar(
                    const SnackBar(content: Text('Daten konnten nicht gespeichert werden.')),
                  );
                }
              } finally {
                if (sheetContext.mounted) setSheetState(() => saving = false);
              }
            }

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  18,
                  18,
                  18,
                  18 + MediaQuery.of(sheetContext).viewInsets.bottom,
                ),
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        'Meine Daten bearbeiten',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Name, Funktion, Eintritt, Status und Filter werden durch die Administration verwaltet.',
                        style: TextStyle(color: Colors.white60),
                      ),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: saving
                            ? null
                            : () async {
                                final picked = await ImagePicker().pickImage(
                                  source: ImageSource.gallery,
                                  imageQuality: 88,
                                  maxWidth: 1600,
                                );
                                if (picked != null) {
                                  setSheetState(() => selectedPhoto = picked);
                                }
                              },
                        icon: const Icon(Icons.photo_camera_outlined),
                        label: Text(
                          selectedPhoto == null
                              ? 'Profilfoto auswählen'
                              : 'Foto gewählt: ${selectedPhoto!.name}',
                        ),
                      ),
                      const SizedBox(height: 10),
                      _ProfileEditField(controller: partner, label: 'Partnerin / Partner'),
                      _ProfileEditField(controller: mobile, label: 'Mobil', keyboardType: TextInputType.phone),
                      _ProfileEditField(controller: privatePhone, label: 'Telefon privat', keyboardType: TextInputType.phone),
                      _ProfileEditField(controller: workPhone, label: 'Telefon Arbeit', keyboardType: TextInputType.phone),
                      _ProfileEditField(controller: email, label: 'E-Mail', keyboardType: TextInputType.emailAddress),
                      _ProfileEditField(controller: address, label: 'Adresse'),
                      _ProfileEditField(controller: occupation, label: 'Beruf'),
                      _ProfileEditField(controller: employer, label: 'Arbeitgeber'),
                      _ProfileEditField(controller: employerUrl, label: 'Webseite Arbeitgeber', keyboardType: TextInputType.url),
                      _ProfileEditField(
                        controller: engagement,
                        label: 'Kurz-Engagement',
                        maxLines: 3,
                      ),
                      const SizedBox(height: 8),
                      FilledButton.icon(
                        onPressed: saving ? null : save,
                        icon: saving
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.save_outlined),
                        label: Text(saving ? 'Speichern …' : 'Speichern'),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );

    if (saved == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Deine Mitgliederdaten wurden aktualisiert.')),
      );
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
        title: Text(
          member.name,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        actions: [
          if (AppStoreScope.of(context).currentUser?['member_id'] == member.id)
            IconButton(
              tooltip: 'Meine Daten bearbeiten',
              onPressed: () => _editOwnProfile(context),
              icon: const Icon(Icons.edit_rounded),
            ),
        ],
      ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          Stack(
            alignment: Alignment.bottomCenter,
            children: [
              GestureDetector(
                onTap: member.photoUrl.isEmpty
                    ? null
                    : () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => FlapImageViewerScreen(
                              title: member.name,
                              imageUrl: member.photoUrl,
                            ),
                          ),
                        ),
                child: Hero(
                  tag: 'member-photo-${member.id ?? member.name}',
                  child: AspectRatio(
                    aspectRatio: 4 / 3,
                    child: member.photoUrl.isNotEmpty
                        ? Image.network(
                            member.photoUrl,
                            headers: headers,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const _ImageError(),
                          )
                        : Container(
                            color: FlapBrand.burgundy,
                            alignment: Alignment.center,
                            child: Text(
                              member.name.isEmpty
                                  ? '?'
                                  : member.name.characters.first,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 76,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                  ),
                ),
              ),
              Container(
                height: 76,
                color: const Color(0xCC090A0B),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _MemberQuickAction(
                      icon: Icons.call_rounded,
                      label: 'Anrufen',
                      enabled: member.phoneMobile.isNotEmpty ||
                          member.phonePrivate.isNotEmpty,
                      onTap: () => _call(
                        context,
                        member.phoneMobile.isNotEmpty
                            ? member.phoneMobile
                            : member.phonePrivate,
                      ),
                    ),
                    _MemberQuickAction(
                      icon: Icons.mail_outline_rounded,
                      label: 'E-Mail',
                      enabled: member.email.isNotEmpty,
                      onTap: () => _mail(context),
                    ),
                    _MemberQuickAction(
                      icon: Icons.chat_bubble_outline_rounded,
                      label: 'Nachricht',
                      enabled: member.phoneMobile.isNotEmpty,
                      onTap: () => _message(context),
                    ),
                    _MemberQuickAction(
                      icon: Icons.forum_outlined,
                      label: 'FLAPAMAMAKU Chat',
                      enabled: true,
                      onTap: () => _openFlapChat(context),
                    ),
                  ],
                ),
              ),
            ],
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
                      const _DarkDivider(),
                      _DarkInfoTile(
                        icon: Icons.volunteer_activism_outlined,
                        title: 'Engagement',
                        value: _value(member.engagement),
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

class _ProfileEditField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final int maxLines;

  const _ProfileEditField({
    required this.controller,
    required this.label,
    this.keyboardType,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        maxLines: maxLines,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          labelText: label,
          filled: true,
          fillColor: const Color(0xFF191B1E),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
    );
  }
}

class _MemberQuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  const _MemberQuickAction({
    required this.icon,
    required this.label,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(14),
      child: SizedBox(
        width: 78,
        height: 68,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              color: enabled ? Colors.white : Colors.white24,
              size: 27,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: enabled ? Colors.white70 : Colors.white24,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
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
