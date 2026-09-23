class NewsItem {
  final String date;
  final String title;
  final String text;
  const NewsItem(this.date, this.title, this.text);
}

class EventItem {
  final String day;
  final String month;
  final String title;
  final String location;
  final String time;
  const EventItem(this.day, this.month, this.title, this.location, this.time);
}

class MemberItem {
  final String name;
  final String role;
  final String since;
  const MemberItem(this.name, this.role, this.since);
}

const newsItems = [
  NewsItem('12.09.2026', 'Start in die neue Fasnachtssaison', 'Mir freued üs uf e schöni Fasnacht mit FLAPAMAMAKU.'),
  NewsItem('28.08.2026', 'Rückblick Sommerhöck', 'Ein gelungener Abend mit vielen schönen Momenten.'),
  NewsItem('15.05.2026', 'Fasnachtsumzug', 'Bilder und Informationen rund um unseren Umzug.'),
];

const eventItems = [
  EventItem('27', 'JAN', 'Rüüdige Samschtig', 'Altstadt Luzern', '14:00 Uhr'),
  EventItem('29', 'JAN', 'SchmuDo', 'Luzern', '05:00 Uhr'),
  EventItem('31', 'JAN', 'GüdisMäntig Vorbereitung', 'Luzern', '14:00 Uhr'),
  EventItem('17', 'FEB', 'Fasnachtsverbrennung', 'Luzern', '19:00 Uhr'),
];

const members = [
  MemberItem('Bruno Meier', 'Präsident', 'seit 2010'),
  MemberItem('Claudia Schmid', 'Vizepräsidentin', 'seit 2012'),
  MemberItem('Markus Huber', 'Kassier', 'seit 2015'),
  MemberItem('Sandra Müller', 'Aktuarin', 'seit 2018'),
  MemberItem('Thomas Steiner', 'Gruppe Laterne', 'seit 2019'),
  MemberItem('Patrick Felder', 'Gruppe Wagen', 'seit 2020'),
];
