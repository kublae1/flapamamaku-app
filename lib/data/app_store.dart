import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/app_data.dart';
import 'api_service.dart';
import 'push_service.dart';

enum UserRole {
  admin,
  mitglied,
}

class AppStore extends ChangeNotifier {
  AppStore({ApiService? api})
      : api = api ?? ApiService(),
        news = List<NewsItem>.from(newsItems),
        events = List<EventItem>.from(eventItems),
        members = List<MemberItem>.from(initialMembers),
        content = <ContentItem>[] {
    pushService = PushService(this.api);
    _sortNews();
    _sortEvents();
    _initialize();
  
  }

  final ApiService api;
  late final PushService pushService;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final LocalAuthentication _localAuth = LocalAuthentication();
  final List<NewsItem> news;
  final List<EventItem> events;
  final List<MemberItem> members;
  final List<MemberFilterItem> memberFilters = <MemberFilterItem>[];
  final List<ContentItem> content;

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
  bool pushEnabled = false;
  bool pushAvailable = false;
  Map<String, dynamic>? currentUser;
  String? authError;
  int themeColorValue = 0xFF8A101B;
  String appName = 'FLAPAMAMAKU';
  String appSubtitle = 'Fasnachtsgruppe Luzern';
  String appLogoUrl = '';
  String clubDescription = '';
  String websiteUrl = '';
  String contactEmail = '';
  String contactPhone = '';
  String clubAddress = '';

  bool showSujet = true;
  String labelSujet = 'Sujet nächstes Jahr';
  bool showArchive = true;
  String labelArchive = 'Vergangene Sujet';
  bool showPhotos = true;
  String labelPhotos = 'Fotoalben';
  bool showDocuments = true;
  String labelDocuments = 'Dokumente';
  bool showPolls = true;
  String labelPolls = 'Umfragen';
  bool showLinks = true;
  String labelLinks = 'Links';

  Color get themeColor => Color(themeColorValue);

  Future<void> _initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final savedServer = prefs.getString('flapamamaku_server_url')?.trim() ?? '';
    if (savedServer.isNotEmpty) {
      api.configureBaseUrl(savedServer);
    }

    themeColorValue =
        prefs.getInt('flapamamaku_brand_color') ?? 0xFF8A101B;
    notifyListeners();

    if (api.isConfigured) {
      await _loadRemoteBranding(prefs);
      await restoreSession();
      _startSyncTimer();
    } else {
      authReady = true;
      isAuthenticated = false;
      notifyListeners();
    }
  }

  void _startSyncTimer() {
    _syncTimer ??= Timer.periodic(
      const Duration(seconds: 30),
      (_) {
        if (isAuthenticated) refreshFromServer();
      },
    );
  }

  Future<void> setThemeColor(int value) async {
    themeColorValue = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('flapamamaku_brand_color', value);
    notifyListeners();
  }

  Future<void> _loadRemoteBranding(SharedPreferences prefs) async {
    try {
      final config = await api.fetchAppConfig();
      final nextName = config['app_name']?.toString().trim() ?? '';
      final nextSubtitle = config['app_subtitle']?.toString().trim() ?? '';
      final colorText = config['primary_color']?.toString().trim() ?? '';
      final nextLogoUrl = config['logo_url']?.toString().trim() ?? '';

      if (nextName.isNotEmpty) appName = nextName;
      appSubtitle = nextSubtitle;
      appLogoUrl = nextLogoUrl;
      clubDescription = config['club_description']?.toString().trim() ?? '';
      websiteUrl = config['website_url']?.toString().trim() ?? '';
      contactEmail = config['contact_email']?.toString().trim() ?? '';
      contactPhone = config['contact_phone']?.toString().trim() ?? '';
      clubAddress = config['club_address']?.toString().trim() ?? '';

      showSujet = config['show_sujet'] != false;
      labelSujet = config['label_sujet']?.toString().trim().isNotEmpty == true
          ? config['label_sujet'].toString().trim()
          : 'Sujet nächstes Jahr';
      showArchive = config['show_archive'] != false;
      labelArchive = config['label_archive']?.toString().trim().isNotEmpty == true
          ? config['label_archive'].toString().trim()
          : 'Vergangene Sujet';
      showPhotos = config['show_photos'] != false;
      labelPhotos = config['label_photos']?.toString().trim().isNotEmpty == true
          ? config['label_photos'].toString().trim()
          : 'Fotoalben';
      showDocuments = config['show_documents'] != false;
      labelDocuments =
          config['label_documents']?.toString().trim().isNotEmpty == true
              ? config['label_documents'].toString().trim()
              : 'Dokumente';
      showPolls = config['show_polls'] != false;
      labelPolls = config['label_polls']?.toString().trim().isNotEmpty == true
          ? config['label_polls'].toString().trim()
          : 'Umfragen';
      showLinks = config['show_links'] != false;
      labelLinks = config['label_links']?.toString().trim().isNotEmpty == true
          ? config['label_links'].toString().trim()
          : 'Links';

      final match = RegExp(r'^#([0-9A-Fa-f]{6})$').firstMatch(colorText);
      if (match != null) {
        themeColorValue = int.parse('FF${match.group(1)!}', radix: 16);
        await prefs.setInt('flapamamaku_brand_color', themeColorValue);
      }
      notifyListeners();
    } catch (_) {
      // Keep the built-in FLAPAMAMAKU defaults when the server is unavailable.
    }
  }
  bool get canNews => currentUser?['can_news'] == true;
  bool get canEvents => currentUser?['can_events'] == true;
  bool get canMembers => currentUser?['can_members'] == true;
  bool get canDocuments => currentUser?['can_documents'] == true;
  bool get canPhotos => currentUser?['can_photos'] == true;
  bool get canGalleryUpload =>
      currentUser?['can_gallery_upload'] == true || canPhotos;
  bool get canPolls => currentUser?['can_polls'] == true;
  bool get canLinks => currentUser?['can_links'] == true;
  bool get canContact => currentUser?['can_contact'] == true;
  bool get canAbout => currentUser?['can_about'] == true;
  bool get canAdminPage => currentUser?['can_admin_page'] == true;
  bool get canManageUsers => currentUser?['can_manage_users'] == true;

  bool canEditContentSection(String section) {
    switch (section) {
      case 'hero':
      case 'sujet':
      case 'archive':
      case 'photos':
      case 'gallery':
        return canPhotos;
      case 'documents':
        return canDocuments;
      case 'polls':
        return canPolls;
      case 'links':
      case 'whatsapp':
        return canLinks;
      default:
        return false;
    }
  }

  bool get canAdminister =>
      !api.isConfigured || canNews || canEvents || canMembers;
  bool get serverConfigured => api.isConfigured;
  String get serverUrl => api.baseUrl;

  Future<bool> changeServerUrl(String value) async {
    var candidate = value.trim();
    while (candidate.endsWith('/')) {
      candidate = candidate.substring(0, candidate.length - 1);
    }

    final uri = Uri.tryParse(candidate);
    if (candidate.isEmpty ||
        uri == null ||
        !(uri.scheme == 'https' || uri.scheme == 'http') ||
        uri.host.isEmpty) {
      authError =
          'Bitte eine gültige Serveradresse mit https:// oder http:// eingeben.';
      notifyListeners();
      return false;
    }

    final previousUrl = api.baseUrl;
    api.configureBaseUrl(candidate);
    try {
      await api.fetchAppConfig();
    } catch (_) {
      api.configureBaseUrl(previousUrl);
      authError =
          'Der Server ist nicht erreichbar oder keine gültige Vereins-App.';
      notifyListeners();
      return false;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('flapamamaku_server_url', candidate);
    await _secureStorage.delete(key: 'flapamamaku_token');

    currentUser = null;
    isAuthenticated = false;
    biometricUnlockPending = false;
    authError = null;
    authReady = true;
    news.clear();
    events.clear();
    members.clear();
    memberFilters.clear();
    content.clear();

    await _loadRemoteBranding(prefs);
    _startSyncTimer();
    notifyListeners();
    return true;
  }

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
    pushEnabled = prefs.getBool('flapamamaku_push_enabled') ?? false;
    pushAvailable = pushService.isConfigured;

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

    // A valid secure session token keeps the member signed in until
    // they explicitly log out or an administrator revokes the session.
    biometricUnlockPending = false;
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
      if (pushEnabled) {
        await pushService.enable();
      }
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
        localizedReason: '$appName entsperren',
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

  Future<bool> loginWithBiometrics() async {
    if (isBiometricAuthenticating) return false;

    try {
      biometricAvailable =
          await _localAuth.canCheckBiometrics &&
          await _localAuth.isDeviceSupported();
    } catch (_) {
      biometricAvailable = false;
    }

    if (!biometricAvailable) {
      authError = 'Auf diesem Gerät ist keine biometrische Anmeldung verfügbar.';
      notifyListeners();
      return false;
    }

    final token = await _secureStorage.read(key: 'flapamamaku_token');
    if (token == null || token.isEmpty) {
      authError =
          'Bitte zuerst einmal mit Benutzername und Passwort anmelden.';
      notifyListeners();
      return false;
    }

    biometricUnlockPending = true;
    notifyListeners();
    return unlockWithBiometrics();
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

  Future<bool> setPushEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();

    if (!enabled) {
      await pushService.disable();
      pushEnabled = false;
      await prefs.setBool('flapamamaku_push_enabled', false);
      notifyListeners();
      return true;
    }

    pushAvailable = pushService.isConfigured;
    if (!pushAvailable) {
      authError = 'Push-Dienst ist noch nicht vollständig eingerichtet.';
      notifyListeners();
      return false;
    }

    final ok = await pushService.enable();
    if (!ok) {
      authError =
          'Push-Benachrichtigungen konnten nicht aktiviert werden. Bitte Berechtigung prüfen.';
      notifyListeners();
      return false;
    }

    pushEnabled = true;
    authError = null;
    await prefs.setBool('flapamamaku_push_enabled', true);
    notifyListeners();
    return true;
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
      if (pushEnabled) {
        await pushService.enable();
      }
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
    await pushService.disable();
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
    memberFilters.clear();
    content.clear();
    _sortNews();
    _sortEvents();
    notifyListeners();
  }

  List<ContentItem> contentFor(String section) {
    return content.where((item) => item.section == section).toList();
  }

  void _sortNews() {
    news.sort((a, b) {
      final aOrder = a.sortOrder;
      final bOrder = b.sortOrder;
      if (aOrder > 0 || bOrder > 0) {
        final normalizedA = aOrder > 0 ? aOrder : 1 << 30;
        final normalizedB = bOrder > 0 ? bOrder : 1 << 30;
        final byOrder = normalizedA.compareTo(normalizedB);
        if (byOrder != 0) return byOrder;
      }
      return b.createdAt.compareTo(a.createdAt);
    });
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
      final remoteMemberFilters = await api.fetchMemberFilters();
      final remoteContent = await api.fetchContent();

      news
        ..clear()
        ..addAll(remoteNews);
      events
        ..clear()
        ..addAll(remoteEvents);
      members
        ..clear()
        ..addAll(remoteMembers);
      memberFilters
        ..clear()
        ..addAll(remoteMemberFilters);
      content
        ..clear()
        ..addAll(remoteContent);

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

  Future<void> deleteContentItem(ContentItem item) async {
    if (item.isSnapshot && item.snapshotId != null) {
      try {
        await api.deleteGallerySnapshot(item.snapshotId!);
        await refreshFromServer();
      } catch (error) {
        syncError = error.toString();
        notifyListeners();
        rethrow;
      }
      return;
    }
    if (item.id == null) return;
    try {
      await api.deleteContent(item.id!);
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
  }

  Future<void> uploadGallerySnapshot({
    required Uint8List bytes,
    required String filename,
    required int expiresDays,
  }) async {
    try {
      await api.uploadGallerySnapshot(
        bytes: bytes,
        filename: filename,
        expiresDays: expiresDays,
      );
      await refreshFromServer();
    } catch (error) {
      syncError = error.toString();
      notifyListeners();
      rethrow;
    }
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

  Future<void> setEventRegistration(
    EventItem event,
    bool registered,
  ) async {
    if (!api.isConfigured || event.id == null) return;
    try {
      await api.setEventRegistration(event.id!, registered);
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
