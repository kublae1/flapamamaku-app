import 'package:flutter/material.dart';
import '../models/app_data.dart';

enum UserRole {
  admin,
  vorstand,
  mitglied,
}

class AppStore extends ChangeNotifier {
  AppStore()
      : news = List<NewsItem>.from(newsItems),
        events = List<EventItem>.from(eventItems),
        members = List<MemberItem>.from(members);

  final List<NewsItem> news;
  final List<EventItem> events;
  final List<MemberItem> members;

  UserRole currentRole = UserRole.admin;

  bool get canAdminister => currentRole == UserRole.admin;

  void setRole(UserRole role) {
    if (role == currentRole) return;
    currentRole = role;
    notifyListeners();
  }

  void addNews(NewsItem item) {
    news.insert(0, item);
    notifyListeners();
  }

  void updateNews(int index, NewsItem item) {
    news[index] = item;
    notifyListeners();
  }

  void deleteNews(int index) {
    news.removeAt(index);
    notifyListeners();
  }

  void addEvent(EventItem item) {
    events.add(item);
    notifyListeners();
  }

  void updateEvent(int index, EventItem item) {
    events[index] = item;
    notifyListeners();
  }

  void deleteEvent(int index) {
    events.removeAt(index);
    notifyListeners();
  }

  void addMember(MemberItem item) {
    members.add(item);
    notifyListeners();
  }

  void updateMember(int index, MemberItem item) {
    members[index] = item;
    notifyListeners();
  }

  void deleteMember(int index) {
    members.removeAt(index);
    notifyListeners();
  }
}

class AppStoreScope extends InheritedNotifier<AppStore> {
  const AppStoreScope({
    required AppStore store,
    required super.child,
    super.key,
  }) : super(notifier: store);

  static AppStore of(BuildContext context) {
    final scope =
        context.dependOnInheritedWidgetOfExactType<AppStoreScope>();
    assert(scope != null, 'AppStoreScope fehlt im Widget-Baum.');
    return scope!.notifier!;
  }
}
