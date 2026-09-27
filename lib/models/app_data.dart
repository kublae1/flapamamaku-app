class PollVoter {
  final String name;
  final int optionIndex;

  const PollVoter({
    required this.name,
    required this.optionIndex,
  });

  factory PollVoter.fromJson(Map<String, dynamic> json) {
    return PollVoter(
      name: json['name']?.toString() ?? '',
      optionIndex: json['option_index'] is int
          ? json['option_index'] as int
          : int.tryParse(json['option_index']?.toString() ?? '') ?? -1,
    );
  }
}

class ContentItem {
  final int? id;
  final String section;
  final String title;
  final String text;
  final String linkUrl;
  final String imageUrl;
  final List<String> imageUrls;
  final String createdAt;
  final int sortOrder;
  final int? snapshotId;
  final bool isSnapshot;
  final bool canDelete;
  final String expiresAt;
  final String documentUrl;
  final String documentName;
  final String documentMime;
  final List<String> pollOptions;
  final List<int> pollCounts;
  final int pollTotalVotes;
  final int? pollMyVote;
  final List<PollVoter> pollVoters;

  const ContentItem({
    this.id,
    required this.section,
    required this.title,
    this.text = '',
    this.linkUrl = '',
    this.imageUrl = '',
    this.imageUrls = const [],
    this.createdAt = '',
    this.sortOrder = 0,
    this.snapshotId,
    this.isSnapshot = false,
    this.canDelete = false,
    this.expiresAt = '',
    this.documentUrl = '',
    this.documentName = '',
    this.documentMime = '',
    this.pollOptions = const [],
    this.pollCounts = const [],
    this.pollTotalVotes = 0,
    this.pollMyVote,
    this.pollVoters = const [],
  });

  factory ContentItem.fromJson(Map<String, dynamic> json) {
    return ContentItem(
      id: json['id'] as int?,
      section: json['section']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      text: json['text']?.toString() ?? '',
      linkUrl: json['link_url']?.toString() ?? '',
      imageUrl: json['image_url']?.toString() ?? '',
      imageUrls: (json['image_urls'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .toList(),
      createdAt: json['created_at']?.toString() ?? '',
      sortOrder: json['sort_order'] as int? ?? 0,
      snapshotId: json['snapshot_id'] as int?,
      isSnapshot: json['is_snapshot'] == true,
      canDelete: json['can_delete'] == true,
      expiresAt: json['expires_at']?.toString() ?? '',
      documentUrl: json['document_url']?.toString() ?? '',
      documentName: json['document_name']?.toString() ?? '',
      documentMime: json['document_mime']?.toString() ?? '',
      pollOptions: (json['poll_options'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .toList(),
      pollCounts: (json['poll_counts'] as List<dynamic>? ?? const [])
          .map((value) => value is int ? value : int.tryParse(value.toString()) ?? 0)
          .toList(),
      pollTotalVotes: json['poll_total_votes'] as int? ?? 0,
      pollMyVote: json['poll_my_vote'] as int?,
      pollVoters: (json['poll_voters'] as List<dynamic>? ?? const [])
          .map((value) => PollVoter.fromJson(
                Map<String, dynamic>.from(value as Map),
              ))
          .where((voter) => voter.name.isNotEmpty && voter.optionIndex >= 0)
          .toList(),
    );
  }
}

class NewsItem {
  final int? id;
  final String date;
  final String title;
  final String text;
  final String createdAt;
  final int sortOrder;
  final String imageAsset;
  final String imageUrl;

  const NewsItem(
    this.date,
    this.title,
    this.text, {
    this.id,
    required this.createdAt,
    this.sortOrder = 0,
    this.imageAsset = '',
    this.imageUrl = '',
  });

  factory NewsItem.fromJson(Map<String, dynamic> json) {
    return NewsItem(
      json['date']?.toString() ?? '',
      json['title']?.toString() ?? '',
      json['text']?.toString() ?? '',
      id: json['id'] as int?,
      createdAt: json['created_at']?.toString() ?? '',
      sortOrder: json['sort_order'] as int? ?? 0,
      imageUrl: json['image_url']?.toString() ?? '',
    );
  }
}

class EventItem {
  final int? id;
  final String eventDate;
  final String day;
  final String month;
  final String title;
  final String location;
  final String time;
  final int registrationCount;
  final bool registeredByMe;

  const EventItem(
    this.day,
    this.month,
    this.title,
    this.location,
    this.time, {
    this.id,
    this.eventDate = '',
    this.registrationCount = 0,
    this.registeredByMe = false,
  });

  String get displayDate {
    final parsed = DateTime.tryParse(eventDate);
    if (parsed == null) return '$day. $month';
    final d = parsed.day.toString().padLeft(2, '0');
    final m = parsed.month.toString().padLeft(2, '0');
    return '$d.$m.${parsed.year}';
  }

  factory EventItem.fromJson(Map<String, dynamic> json) {
    return EventItem(
      json['day']?.toString() ?? '',
      json['month']?.toString() ?? '',
      json['title']?.toString() ?? '',
      json['location']?.toString() ?? '',
      json['time']?.toString() ?? '',
      id: json['id'] as int?,
      eventDate: json['event_date']?.toString() ?? '',
      registrationCount: json['registration_count'] as int? ?? 0,
      registeredByMe: json['registered_by_me'] == true,
    );
  }
}

class MemberFilterItem {
  final int id;
  final String label;
  final bool active;
  final int sortOrder;

  const MemberFilterItem({
    required this.id,
    required this.label,
    required this.active,
    required this.sortOrder,
  });

  factory MemberFilterItem.fromJson(Map<String, dynamic> json) {
    return MemberFilterItem(
      id: json['id'] as int? ?? 0,
      label: json['label']?.toString() ?? '',
      active: json['active'] == true,
      sortOrder: json['sort_order'] as int? ?? 0,
    );
  }
}

class MemberItem {
  final int? id;
  final String name;
  final String role;
  final String since;
  final String birthDate;
  final String status;
  final String memberGroup;
  final String engagement;
  final int sortOrder;
  final List<int> filterIds;
  final String partnerName;
  final String phoneMobile;
  final String phonePrivate;
  final String phoneWork;
  final String email;
  final String address;
  final String occupation;
  final String employer;
  final String employerUrl;
  final String photoUrl;

  const MemberItem(
    this.name,
    this.role,
    this.since, {
    this.id,
    this.birthDate = '',
    this.status = 'Aktiv',
    this.memberGroup = '',
    this.engagement = '',
    this.sortOrder = 0,
    this.filterIds = const [],
    this.partnerName = '',
    this.phoneMobile = '',
    this.phonePrivate = '',
    this.phoneWork = '',
    this.email = '',
    this.address = '',
    this.occupation = '',
    this.employer = '',
    this.employerUrl = '',
    this.photoUrl = '',
  });

  factory MemberItem.fromJson(Map<String, dynamic> json) {
    final legacyPhone = json['phone']?.toString() ?? '';
    return MemberItem(
      json['name']?.toString() ?? '',
      json['role']?.toString() ?? 'Präsident',
      json['since']?.toString() ?? '',
      id: json['id'] as int?,
      birthDate: json['birth_date']?.toString() ?? '',
      status: json['status']?.toString() ?? 'Aktiv',
      memberGroup: json['member_group']?.toString() ?? '',
      engagement: json['engagement']?.toString() ?? '',
      sortOrder: json['sort_order'] as int? ?? 0,
      filterIds: (json['filter_ids'] as List<dynamic>? ?? const [])
          .map((value) => value is int ? value : int.tryParse(value.toString()) ?? 0)
          .where((value) => value > 0)
          .toList(),
      partnerName: json['partner_name']?.toString() ?? '',
      phoneMobile:
          json['phone_mobile']?.toString().isNotEmpty == true
              ? json['phone_mobile'].toString()
              : legacyPhone,
      phonePrivate: json['phone_private']?.toString() ?? '',
      phoneWork: json['phone_work']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
      occupation: json['occupation']?.toString() ?? '',
      employer: json['employer']?.toString() ?? '',
      employerUrl: json['employer_url']?.toString() ?? '',
      photoUrl: json['photo_url']?.toString() ?? '',
    );
  }
}

const newsItems = [
  NewsItem(
    '12.09.2026',
    'Start in die neue Fasnachtssaison',
    'Mir freued üs uf e schöni Fasnacht mit FLAPAMAMAKU.',
    createdAt: '2026-09-12T12:00:00',
    imageAsset: 'assets/images/year_motto_pig_rockers.jpg',
  ),
  NewsItem(
    '28.08.2026',
    'Rückblick Sommerhöck',
    'Ein gelungener Abend mit vielen schönen Momenten.',
    createdAt: '2026-08-28T12:00:00',
  ),
  NewsItem(
    '15.05.2026',
    'Fasnachtsumzug',
    'Bilder und Informationen rund um unseren Umzug.',
    createdAt: '2026-05-15T12:00:00',
    imageAsset: 'assets/images/archive_top_hats_night.jpg',
  ),
];

const eventItems = [
  EventItem(
    '27',
    'JAN',
    'Rüüdige Samschtig',
    'Altstadt Luzern',
    '14:00 Uhr',
    eventDate: '2027-01-27',
  ),
  EventItem(
    '29',
    'JAN',
    'SchmuDo',
    'Luzern',
    '05:00 Uhr',
    eventDate: '2027-01-29',
  ),
  EventItem(
    '31',
    'JAN',
    'GüdisMäntig Vorbereitung',
    'Luzern',
    '14:00 Uhr',
    eventDate: '2027-01-31',
  ),
  EventItem(
    '17',
    'FEB',
    'Fasnachtsverbrennung',
    'Luzern',
    '19:00 Uhr',
    eventDate: '2027-02-17',
  ),
];

const initialMembers = [
  MemberItem('Bruno Meier', 'Präsident', 'seit 2010'),
  MemberItem('Claudia Schmid', 'Präsidentin', 'seit 2012'),
  MemberItem('Markus Huber', 'Präsident', 'seit 2015'),
  MemberItem('Sandra Müller', 'Präsidentin', 'seit 2018'),
  MemberItem('Thomas Steiner', 'Präsident', 'seit 2019'),
  MemberItem('Patrick Felder', 'Präsident', 'seit 2020'),
];
