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
    _sortEvents();

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

  void _sortEvents() {
    events.sort((a, b) {
      final aDate = DateTime.tryParse(a.eventDate);
      final bDate = DateTime.tryParse(b.eventDate);
      if (aDate == null && bDate == null) return 0;
      if (aDate == null) return 1;
      if (bDate == null) return -1;
      final dateCompare = aDate.compareTo(bDate);
      if (dateCompare != 0) return dateCompare;
      return a.time.compareTo(b.time);
    });
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
      _sortEvents();
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

  Future<void> addNews(NewsItem item) async {
    if (!api.isConfigured) {
      news.add(item);
      _sortNews();
      notifyListeners();
      return;
    }
    try {
      await api.saveNews(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> updateNews(int index, NewsItem item) async {
    if (!api.isConfigured) {
      news[index] = item;
      _sortNews();
      notifyListeners();
      return;
    }
    try {
      await api.saveNews(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteNews(int index) async {
    final item = news[index];
    if (!api.isConfigured || item.id == null) {
      news.removeAt(index);
      notifyListeners();
      return;
    }
    try {
      await api.deleteNews(item.id!);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> addEvent(EventItem item) async {
    if (!api.isConfigured) {
      events.add(item);
      _sortEvents();
      notifyListeners();
      return;
    }
    try {
      await api.saveEvent(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> updateEvent(int index, EventItem item) async {
    if (!api.isConfigured) {
      events[index] = item;
      _sortEvents();
      notifyListeners();
      return;
    }
    try {
      await api.saveEvent(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteEvent(int index) async {
    final item = events[index];
    if (!api.isConfigured || item.id == null) {
      events.removeAt(index);
      notifyListeners();
      return;
    }
    try {
      await api.deleteEvent(item.id!);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> addMember(MemberItem item) async {
    if (!api.isConfigured) {
      members.add(item);
      notifyListeners();
      return;
    }
    try {
      await api.saveMember(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> updateMember(int index, MemberItem item) async {
    if (!api.isConfigured) {
      members[index] = item;
      notifyListeners();
      return;
    }
    try {
      await api.saveMember(item);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> deleteMember(int index) async {
    final item = members[index];
    if (!api.isConfigured || item.id == null) {
      members.removeAt(index);
      notifyListeners();
      return;
    }
    try {
      await api.deleteMember(item.id!);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
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
