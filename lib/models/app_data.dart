class NewsItem {
  final int? id;
  final String date;
  final String title;
  final String text;
  final String createdAt;
  final String imageAsset;
  final String imageUrl;

  const NewsItem(
    this.date,
    this.title,
    this.text, {
    this.id,
    required this.createdAt,
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
      imageUrl: json['image_url']?.toString() ?? '',
    );
  }
}

class EventItem {
  final int? id;
  final String day;
  final String month;
  final String title;
  final String location;
  final String time;

  const EventItem(
    this.day,
    this.month,
    this.title,
    this.location,
    this.time, {
    this.id,
  });

  factory EventItem.fromJson(Map<String, dynamic> json) {
    return EventItem(
      json['day']?.toString() ?? '',
      json['month']?.toString() ?? '',
      json['title']?.toString() ?? '',
      json['location']?.toString() ?? '',
      json['time']?.toString() ?? '',
      id: json['id'] as int?,
    );
  }
}

class MemberItem {
  final int? id;
  final String name;
  final String role;
  final String since;
  final String partnerName;
  final String phone;
  final String email;
  final String address;

  const MemberItem(
    this.name,
    this.role,
    this.since, {
    this.id,
    this.partnerName = '',
    this.phone = '',
    this.email = '',
    this.address = '',
  });

  factory MemberItem.fromJson(Map<String, dynamic> json) {
    return MemberItem(
      json['name']?.toString() ?? '',
      json['role']?.toString() ?? 'Präsident',
      json['since']?.toString() ?? '',
      id: json['id'] as int?,
      partnerName: json['partner_name']?.toString() ?? '',
      phone: json['phone']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
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
  EventItem('27', 'JAN', 'Rüüdige Samschtig', 'Altstadt Luzern', '14:00 Uhr'),
  EventItem('29', 'JAN', 'SchmuDo', 'Luzern', '05:00 Uhr'),
  EventItem(
    '31',
    'JAN',
    'GüdisMäntig Vorbereitung',
    'Luzern',
    '14:00 Uhr',
  ),
  EventItem(
    '17',
    'FEB',
    'Fasnachtsverbrennung',
    'Luzern',
    '19:00 Uhr',
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
