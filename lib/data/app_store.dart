import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
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
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final LocalAuthentication _localAuth = LocalAuthentication();
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
  bool biometricEnabled = false;
  bool biometricAvailable = false;
  bool biometricUnlockPending = false;
  bool isBiometricAuthenticating = false;
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
    biometricEnabled =
        prefs.getBool('flapamamaku_biometric_enabled') ?? false;

    try {
      biometricAvailable =
          await _localAuth.canCheckBiometrics &&
          await _localAuth.isDeviceSupported();
    } catch (_) {
      biometricAvailable = false;
    }

    final token = await _secureStorage.read(key: 'flapamamaku_token');
    if (token == null || token.isEmpty) {
      api.setToken(null);
      authReady = true;
      isAuthenticated = false;
      biometricUnlockPending = false;
      notifyListeners();
      return;
    }

    if (biometricEnabled && biometricAvailable) {
      api.setToken(null);
      biometricUnlockPending = true;
      authReady = true;
      isAuthenticated = false;
      notifyListeners();
      return;
    }

    await _restoreWithToken(token);
  }

  Future<void> _restoreWithToken(String token) async {
    api.setToken(token);
    try {
      currentUser = await api.fetchMe();
      isAuthenticated = true;
      biometricUnlockPending = false;
      authError = null;
      await refreshFromServer();
    } catch (_) {
      api.setToken(null);
      currentUser = null;
      isAuthenticated = false;
      biometricUnlockPending = false;
      await _secureStorage.delete(key: 'flapamamaku_token');
    } finally {
      authReady = true;
      notifyListeners();
    }
  }

  Future<bool> unlockWithBiometrics() async {
    if (!biometricUnlockPending || isBiometricAuthenticating) return false;

    isBiometricAuthenticating = true;
    authError = null;
    notifyListeners();

    try {
      final authenticated = await _localAuth.authenticate(
        localizedReason: 'FLAPAMAMAKU entsperren',
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );

      if (!authenticated) return false;

      final token = await _secureStorage.read(key: 'flapamamaku_token');
      if (token == null || token.isEmpty) {
        biometricUnlockPending = false;
        return false;
      }

      await _restoreWithToken(token);
      return isAuthenticated;
    } catch (_) {
      authError = 'Biometrische Anmeldung konnte nicht verwendet werden.';
      return false;
    } finally {
      isBiometricAuthenticating = false;
      notifyListeners();
    }
  }

  Future<void> usePasswordInstead() async {
    api.setToken(null);
    currentUser = null;
    isAuthenticated = false;
    biometricUnlockPending = false;
    authError = null;
    authReady = true;
    notifyListeners();
  }

  Future<bool> setBiometricEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();

    if (!enabled) {
      biometricEnabled = false;
      await prefs.setBool('flapamamaku_biometric_enabled', false);
      notifyListeners();
      return true;
    }

    try {
      biometricAvailable =
          await _localAuth.canCheckBiometrics &&
          await _localAuth.isDeviceSupported();
      if (!biometricAvailable) {
        authError = 'Auf diesem Gerät ist keine biometrische Anmeldung verfügbar.';
        notifyListeners();
        return false;
      }

      final authenticated = await _localAuth.authenticate(
        localizedReason: 'Biometrische Anmeldung für FLAPAMAMAKU aktivieren',
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
      if (!authenticated) return false;

      biometricEnabled = true;
      authError = null;
      await prefs.setBool('flapamamaku_biometric_enabled', true);
      notifyListeners();
      return true;
    } catch (_) {
      authError = 'Biometrische Anmeldung konnte nicht aktiviert werden.';
      notifyListeners();
      return false;
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

      await _secureStorage.write(
        key: 'flapamamaku_token',
        value: token,
      );
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
    await _secureStorage.delete(key: 'flapamamaku_token');
    currentUser = null;
    isAuthenticated = false;
    biometricUnlockPending = false;
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
