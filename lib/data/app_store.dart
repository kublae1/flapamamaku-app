import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
      restoreSession();
      _syncTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) {
          if (isAuthenticated) refreshFromServer();
        },
      );
    } else {
      authReady = true;
      isAuthenticated = true;
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
  bool authReady = false;
  bool isAuthenticated = false;
  bool isAuthenticating = false;
  Map<String, dynamic>? currentUser;
  String? authError;

  bool get canNews => currentUser?['can_news'] == true;
  bool get canEvents => currentUser?['can_events'] == true;
  bool get canMembers => currentUser?['can_members'] == true;
  bool get canDocuments => currentUser?['can_documents'] == true;
  bool get canPhotos => currentUser?['can_photos'] == true;
  bool get canPolls => currentUser?['can_polls'] == true;
  bool get canLinks => currentUser?['can_links'] == true;
  bool get canContact => currentUser?['can_contact'] == true;
  bool get canAbout => currentUser?['can_about'] == true;
  bool get canAdminPage => currentUser?['can_admin_page'] == true;
  bool get canManageUsers => currentUser?['can_manage_users'] == true;

  bool get canAdminister =>
      !api.isConfigured || canNews || canEvents || canMembers;
  bool get serverConfigured => api.isConfigured;

  String get signedInName =>
      currentUser?['member_name']?.toString().isNotEmpty == true
          ? currentUser!['member_name'].toString()
          : currentUser?['username']?.toString() ?? '';

  Future<void> restoreSession() async {
    authReady = false;
    notifyListeners();

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('flapamamaku_token');
    if (token == null || token.isEmpty) {
      api.setToken(null);
      authReady = true;
      isAuthenticated = false;
      notifyListeners();
      return;
    }

    api.setToken(token);
    try {
      currentUser = await api.fetchMe();
      isAuthenticated = true;
      authError = null;
      await refreshFromServer();
    } catch (_) {
      api.setToken(null);
      currentUser = null;
      isAuthenticated = false;
      await prefs.remove('flapamamaku_token');
    } finally {
      authReady = true;
      notifyListeners();
    }
  }

  Future<bool> login(String username, String password) async {
    if (!api.isConfigured) return true;

    isAuthenticating = true;
    authError = null;
    notifyListeners();

    try {
      final result = await api.login(username.trim(), password);
      final token = result['token']?.toString() ?? '';
      if (token.isEmpty) {
        throw const ApiException('Kein Sitzungstoken erhalten.');
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('flapamamaku_token', token);
      currentUser = Map<String, dynamic>.from(
        result['user'] as Map<String, dynamic>,
      );
      isAuthenticated = true;
      await refreshFromServer();
      return true;
    } catch (error) {
      authError = 'Benutzername oder Passwort falsch.';
      isAuthenticated = false;
      currentUser = null;
      return false;
    } finally {
      isAuthenticating = false;
      authReady = true;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    try {
      await api.logout();
    } catch (_) {
      api.setToken(null);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('flapamamaku_token');
    currentUser = null;
    isAuthenticated = false;
    authError = null;
    news
      ..clear()
      ..addAll(newsItems);
    events
      ..clear()
      ..addAll(eventItems);
    members
      ..clear()
      ..addAll(initialMembers);
    _sortNews();
    _sortEvents();
    notifyListeners();
  }

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
    if (!api.isConfigured || !isAuthenticated || isSyncing) return;

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
