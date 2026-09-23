import 'dart:async';

import 'package:flutter/material.dart';

import '../models/app_data.dart';
import 'api_service.dart';

enum UserRole {
  admin,
  mitglied,
}

class AppStore extends ChangeNotifier {
  AppStore({ApiService? api})
      : api = api ?? ApiService(),
        news = List<NewsItem>.from(newsItems),
        events = List<EventItem>.from(eventItems),
        members = List<MemberItem>.from(initialMembers) {
    _sortNews();

    if (this.api.isConfigured) {
      refreshFromServer();
      _syncTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => refreshFromServer(),
      );
    }
  }

  final ApiService api;
  final List<NewsItem> news;
  final List<EventItem> events;
  final List<MemberItem> members;

  Timer? _syncTimer;
  bool isSyncing = false;
  bool isUsingServer = false;
  String? syncError;
  DateTime? lastSuccessfulSync;

  UserRole currentRole = UserRole.admin;

  bool get canAdminister => currentRole == UserRole.admin;
  bool get serverConfigured => api.isConfigured;

  void _sortNews() {
    news.sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  Future<void> refreshFromServer() async {
    if (!api.isConfigured || isSyncing) return;

    isSyncing = true;
    notifyListeners();

    try {
      final remoteNews = await api.fetchNews();
      final remoteEvents = await api.fetchEvents();
      final remoteMembers = await api.fetchMembers();

      news
        ..clear()
        ..addAll(remoteNews);
      events
        ..clear()
        ..addAll(remoteEvents);
      members
        ..clear()
        ..addAll(remoteMembers);

      _sortNews();
      isUsingServer = true;
      syncError = null;
      lastSuccessfulSync = DateTime.now();
    } catch (error) {
      syncError = error.toString();
    } finally {
      isSyncing = false;
      notifyListeners();
    }
  }

  void setRole(UserRole role) {
    if (role == currentRole) return;
    currentRole = role;
    notifyListeners();
  }

  void addNews(NewsItem item) {
    news.add(item);
    _sortNews();
    notifyListeners();
  }

  void updateNews(int index, NewsItem item) {
    news[index] = item;
    _sortNews();
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

  @override
  void dispose() {
    _syncTimer?.cancel();
    super.dispose();
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
