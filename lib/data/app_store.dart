import 'dart:async';
import 'dart:convert';
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
  AppStore({ApiService? api, bool initialize = true})
      : api = api ?? ApiService(),
        news = List<NewsItem>.from(newsItems),
        events = List<EventItem>.from(eventItems),
        members = List<MemberItem>.from(initialMembers),
        content = <ContentItem>[] {
    pushService = PushService(this.api);
    _sortNews();
    _sortEvents();
    if (initialize) {
      _initialize();
    }
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
  String? _pendingForcedPassword;
  final List<Map<String, dynamic>> accessibleClubs = <Map<String, dynamic>>[];
  bool clubSelectionRequired = false;
  String? authError;
  int themeColorValue = 0xFF8A101B;
  String appName = const String.fromEnvironment(
    'APP_NAME',
    defaultValue: 'FLAPAMAMAKU',
  );
  String appSubtitle = const String.fromEnvironment(
    'APP_SUBTITLE',
    defaultValue: 'Fasnachtsgruppe Luzern',
  );
  String appLogoUrl = '';
  String clubDescription = '';
  String websiteUrl = '';
  String contactEmail = '';
  String contactPhone = '';
  String clubAddress = '';

  bool showNews = true;
  bool showEvents = true;
  bool showMembers = true;
  bool showGallery = true;
  bool showPushNotifications = true;
  bool showCalendar = true;
  bool showParticipantLists = true;

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

  void _resetToNeutralBranding() {
    themeColorValue = 0xFF6B7280;
    appName = 'Vereins-App';
    appSubtitle = 'Bitte anmelden';
    appLogoUrl = '';
    clubDescription = '';
    websiteUrl = '';
    contactEmail = '';
    contactPhone = '';
    clubAddress = '';

    showNews = true;
    showEvents = true;
    showMembers = true;
    showGallery = true;
    showPushNotifications = true;
    showCalendar = true;
    showParticipantLists = true;
    showSujet = true;
    labelSujet = 'Sujet nächstes Jahr';
    showArchive = true;
    labelArchive = 'Vergangene Sujet';
    showPhotos = true;
    labelPhotos = 'Fotoalben';
    showDocuments = true;
    labelDocuments = 'Dokumente';
    showPolls = true;
    labelPolls = 'Umfragen';
    showLinks = true;
    labelLinks = 'Links';
  }

  Color get themeColor => Color(themeColorValue);

  String get _offlineCacheKey =>
      'flapamamaku_offline_cache_${Uri.encodeComponent(api.baseUrl)}';

  Map<String, dynamic> _brandingSnapshot() => {
        'app_name': appName,
        'app_subtitle': appSubtitle,
        'app_logo_url': appLogoUrl,
        'club_description': clubDescription,
        'website_url': websiteUrl,
        'contact_email': contactEmail,
        'contact_phone': contactPhone,
        'club_address': clubAddress,
        'theme_color_value': themeColorValue,
        'show_news': showNews,
        'show_events': showEvents,
        'show_members': showMembers,
        'show_gallery': showGallery,
        'show_push_notifications': showPushNotifications,
        'show_calendar': showCalendar,
        'show_participant_lists': showParticipantLists,
        'show_sujet': showSujet,
        'label_sujet': labelSujet,
        'show_archive': showArchive,
        'label_archive': labelArchive,
        'show_photos': showPhotos,
        'label_photos': labelPhotos,
        'show_documents': showDocuments,
        'label_documents': labelDocuments,
        'show_polls': showPolls,
        'label_polls': labelPolls,
        'show_links': showLinks,
        'label_links': labelLinks,
      };

  void _applyCachedBranding(Map<String, dynamic> value) {
    appName = value['app_name']?.toString().trim().isNotEmpty == true
        ? value['app_name'].toString().trim()
        : appName;
    appSubtitle = value['app_subtitle']?.toString() ?? appSubtitle;
    appLogoUrl = value['app_logo_url']?.toString() ?? appLogoUrl;
    clubDescription = value['club_description']?.toString() ?? clubDescription;
    websiteUrl = value['website_url']?.toString() ?? websiteUrl;
    contactEmail = value['contact_email']?.toString() ?? contactEmail;
    contactPhone = value['contact_phone']?.toString() ?? contactPhone;
    clubAddress = value['club_address']?.toString() ?? clubAddress;
    themeColorValue = value['theme_color_value'] is int
        ? value['theme_color_value'] as int
        : themeColorValue;
    showNews = value['show_news'] != false;
    showEvents = value['show_events'] != false;
    showMembers = value['show_members'] != false;
    showGallery = value['show_gallery'] != false;
    showPushNotifications = value['show_push_notifications'] != false;
    showCalendar = value['show_calendar'] != false;
    showParticipantLists = value['show_participant_lists'] != false;
    showSujet = value['show_sujet'] != false;
    labelSujet = value['label_sujet']?.toString() ?? labelSujet;
    showArchive = value['show_archive'] != false;
    labelArchive = value['label_archive']?.toString() ?? labelArchive;
    showPhotos = value['show_photos'] != false;
    labelPhotos = value['label_photos']?.toString() ?? labelPhotos;
    showDocuments = value['show_documents'] != false;
    labelDocuments = value['label_documents']?.toString() ?? labelDocuments;
    showPolls = value['show_polls'] != false;
    labelPolls = value['label_polls']?.toString() ?? labelPolls;
    showLinks = value['show_links'] != false;
    labelLinks = value['label_links']?.toString() ?? labelLinks;
  }

  Future<void> _saveOfflineCache() async {
    if (!api.isConfigured || currentUser == null) return;
    final prefs = await SharedPreferences.getInstance();
    final syncedAt = lastSuccessfulSync ?? DateTime.now();
    final payload = {
      'version': 1,
      'server_url': api.baseUrl,
      'saved_at': syncedAt.toIso8601String(),
      'current_user': currentUser,
      'branding': _brandingSnapshot(),
      'news': news.map((item) => item.toJson()).toList(),
      'events': events.map((item) => item.toJson()).toList(),
      'members': members.map((item) => item.toJson()).toList(),
      'member_filters':
          memberFilters.map((item) => item.toJson()).toList(),
      'content': content.map((item) => item.toJson()).toList(),
    };
    await prefs.setString(_offlineCacheKey, jsonEncode(payload));
  }

  Future<bool> _loadOfflineCache() async {
    if (!api.isConfigured) return false;
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_offlineCacheKey);
    if (raw == null || raw.trim().isEmpty) return false;

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) return false;
      final data = Map<String, dynamic>.from(decoded);
      if (data['server_url']?.toString() != api.baseUrl) return false;

      final cachedUser = data['current_user'];
      if (cachedUser is! Map) return false;
      currentUser = Map<String, dynamic>.from(cachedUser);
      isAuthenticated = true;

      final branding = data['branding'];
      if (branding is Map) {
        _applyCachedBranding(Map<String, dynamic>.from(branding));
      }

      List<Map<String, dynamic>> listOfMaps(String key) {
        return (data[key] as List<dynamic>? ?? const [])
            .whereType<Map>()
            .map((value) => Map<String, dynamic>.from(value))
            .toList();
      }

      news
        ..clear()
        ..addAll(listOfMaps('news').map(NewsItem.fromJson));
      events
        ..clear()
        ..addAll(listOfMaps('events').map(EventItem.fromJson));
      members
        ..clear()
        ..addAll(listOfMaps('members').map(MemberItem.fromJson));
      memberFilters
        ..clear()
        ..addAll(listOfMaps('member_filters').map(MemberFilterItem.fromJson));
      content
        ..clear()
        ..addAll(listOfMaps('content').map(ContentItem.fromJson));

      _sortNews();
      _sortEvents();
      isUsingServer = false;
      syncError = 'Offline – gespeicherte Daten werden angezeigt.';
      lastSuccessfulSync = DateTime.tryParse(
        data['saved_at']?.toString() ?? '',
      );
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> _initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final savedServer = prefs.getString('flapamamaku_server_url')?.trim() ?? '';
    if (savedServer.isNotEmpty) {
      // Existing installations may already be provisioned for a specific
      // club server. Keep that routing even when server controls are hidden
      // from normal members.
      api.configureBaseUrl(savedServer);
    } else if (!_allowServerChange) {
      // A previous managed-server build may have removed the saved URL.
      // Recover the most recently used club server from the authenticated
      // offline cache so existing members are not redirected to another club.
      String recoveredServer = '';
      DateTime? recoveredAt;
      for (final key in prefs.getKeys()) {
        if (!key.startsWith('flapamamaku_offline_cache_')) continue;
        final raw = prefs.getString(key);
        if (raw == null || raw.trim().isEmpty) continue;
        try {
          final decoded = jsonDecode(raw);
          if (decoded is! Map) continue;
          final data = Map<String, dynamic>.from(decoded);
          final server = data['server_url']?.toString().trim() ?? '';
          if (server.isEmpty) continue;
          final savedAt = DateTime.tryParse(data['saved_at']?.toString() ?? '');
          if (recoveredServer.isEmpty ||
              (savedAt != null &&
                  (recoveredAt == null || savedAt.isAfter(recoveredAt)))) {
            recoveredServer = server;
            recoveredAt = savedAt;
          }
        } catch (_) {
          // Ignore malformed legacy cache entries.
        }
      }
      if (recoveredServer.isNotEmpty) {
        api.configureBaseUrl(recoveredServer);
        await prefs.setString('flapamamaku_server_url', recoveredServer);
      }
    }

    // Before authentication the app must stay completely neutral.
    // Never reuse the last club's cached branding on startup.
    _resetToNeutralBranding();
    notifyListeners();

    if (api.isConfigured) {
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
        if (isAuthenticated && !mustChangePassword) refreshFromServer();
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

      showNews = config['show_news'] != false;
      showEvents = config['show_events'] != false;
      showMembers = config['show_members'] != false;
      showGallery = config['show_gallery'] != false;
      showPushNotifications = config['show_push_notifications'] != false;
      showCalendar = config['show_calendar'] != false;
      showParticipantLists = config['show_participant_lists'] != false;
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
      if (isAuthenticated) {
        await _saveOfflineCache();
      }
      notifyListeners();
    } catch (_) {
      // Cached branding remains available when the server is unavailable.
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
  static const bool _allowServerChange = bool.fromEnvironment(
    'ALLOW_SERVER_CHANGE',
    defaultValue: false,
  );

  bool get serverConfigured => api.isConfigured;
  String? get pushDiagnostic => pushService.lastError;
  String get serverUrl => api.baseUrl;
  bool get canChangeServer => _allowServerChange;

  String userMessageForError(
    Object error, {
    String fallback = 'Die Aktion konnte nicht abgeschlossen werden.',
  }) =>
      friendlyErrorMessage(error, fallback: fallback);

  Future<bool> changeServerUrl(String value) async {
    if (!_allowServerChange) {
      authError = 'Die Serveradresse wird zentral verwaltet.';
      notifyListeners();
      return false;
    }
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
    } catch (error) {
      api.configureBaseUrl(previousUrl);
      authError = friendlyErrorMessage(
        error,
        fallback: 'Der Server ist nicht erreichbar oder keine gültige Vereins-App.',
      );
      notifyListeners();
      return false;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('flapamamaku_server_url', candidate);
    await _secureStorage.delete(key: 'flapamamaku_token');

    currentUser = null;
    accessibleClubs.clear();
    clubSelectionRequired = false;
    isAuthenticated = false;
    biometricUnlockPending = false;
    authError = null;
    authReady = true;
    news.clear();
    events.clear();
    members.clear();
    memberFilters.clear();
    content.clear();

    _resetToNeutralBranding();
    _startSyncTimer();
    notifyListeners();
    return true;
  }

  String get signedInName =>
      currentUser?['member_name']?.toString().isNotEmpty == true
          ? currentUser!['member_name'].toString()
          : currentUser?['username']?.toString() ?? '';

  int? get currentClubId {
    final value = currentUser?['current_club_id'];
    return value is int ? value : int.tryParse(value?.toString() ?? '');
  }

  bool get isSuperAdmin => currentUser?['is_super_admin'] == true;
  bool get mustChangePassword => currentUser?['must_change_password'] == true;
  bool get hasPendingForcedPassword =>
      _pendingForcedPassword?.isNotEmpty == true;

  Future<bool> changeForcedPassword(String newPassword) async {
    final currentPassword = _pendingForcedPassword;
    if (currentPassword == null || currentPassword.isEmpty) {
      authError =
          'Bitte erneut mit Benutzername und Passwort anmelden, bevor das Passwort geändert wird.';
      await logout();
      return false;
    }
    final ok = await changePassword(currentPassword, newPassword);
    if (ok) {
      _pendingForcedPassword = null;
    }
    return ok;
  }

  Future<bool> changePassword(
    String currentPassword,
    String newPassword,
  ) async {
    try {
      currentUser = await api.changePassword(currentPassword, newPassword);
      authError = null;

      if (!mustChangePassword) {
        await _loadAccessibleClubs();
        clubSelectionRequired = isSuperAdmin && accessibleClubs.length > 1;
        final prefs = await SharedPreferences.getInstance();
        await _loadRemoteBranding(prefs);
        await refreshFromServer();
        if (pushEnabled && showPushNotifications) {
          await pushService.enable();
        }
      }

      notifyListeners();
      return true;
    } catch (error) {
      authError = friendlyErrorMessage(
        error,
        fallback: 'Passwort konnte nicht geändert werden.',
      );
      notifyListeners();
      return false;
    }
  }

  bool get canSwitchClub => isSuperAdmin && accessibleClubs.length > 1;

  String get currentClubName {
    final clubId = currentClubId;
    for (final club in accessibleClubs) {
      final rawId = club['id'];
      final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
      if (id == clubId) {
        return club['name']?.toString() ?? appName;
      }
    }
    return appName;
  }

  Future<void> _loadAccessibleClubs() async {
    accessibleClubs
      ..clear()
      ..addAll(await api.fetchAccessibleClubs());
  }

  void _clearClubData() {
    news.clear();
    events.clear();
    members.clear();
    memberFilters.clear();
    content.clear();
    syncError = null;
    lastSuccessfulSync = null;
  }

  Future<bool> selectClub(int clubId) async {
    if (!isAuthenticated || !api.isConfigured) return false;
    try {
      await api.switchClub(clubId);
      currentUser = await api.fetchMe();
      await _loadAccessibleClubs();
      clubSelectionRequired = false;
      _clearClubData();
      final prefs = await SharedPreferences.getInstance();
      await _loadRemoteBranding(prefs);
      await refreshFromServer();
      if (pushEnabled && showPushNotifications) {
        await pushService.enable();
      }
      notifyListeners();
      return true;
    } catch (error) {
      authError = friendlyErrorMessage(
        error,
        fallback: 'Verein konnte nicht gewechselt werden.',
      );
      notifyListeners();
      return false;
    }
  }

  Future<void> restoreSession() async {
    authReady = false;
    notifyListeners();

    final prefs = await SharedPreferences.getInstance();
    biometricEnabled =
        prefs.getBool('flapamamaku_biometric_enabled') ?? false;
    pushEnabled = prefs.getBool('flapamamaku_push_enabled') ?? false;
    pushAvailable = pushService.isConfigured;

    try {
      biometricAvailable = await _localAuth.isDeviceSupported();
      if (!biometricAvailable) {
        biometricAvailable = await _localAuth.canCheckBiometrics;
      }
    } catch (_) {
      biometricAvailable = false;
    }

    final token = await _secureStorage.read(key: 'flapamamaku_token');
    if (token == null || token.isEmpty) {
      api.setToken(null);
      currentUser = null;
      accessibleClubs.clear();
      clubSelectionRequired = false;
      isAuthenticated = false;
      biometricUnlockPending = false;
      _resetToNeutralBranding();
      authReady = true;
      notifyListeners();
      return;
    }

    // When device authentication is enabled, never restore the secured
    // session before the user has unlocked this app instance.
    if (biometricEnabled && biometricAvailable) {
      biometricUnlockPending = true;
      isAuthenticated = false;
      currentUser = null;
      authReady = true;
      notifyListeners();
      return;
    }

    // Without the optional device lock, a valid secure session token keeps
    // the member signed in until logout or server-side session revocation.
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
      clubSelectionRequired = false;

      if (mustChangePassword) {
        // A restored long-lived session has no freshly verified password in
        // memory. Require one normal login before the mandatory password
        // change so we never keep or persist the old password.
        api.setToken(null);
        currentUser = null;
        accessibleClubs.clear();
        clubSelectionRequired = false;
        isAuthenticated = false;
        biometricUnlockPending = false;
        await _secureStorage.delete(key: 'flapamamaku_token');
        _resetToNeutralBranding();
        return;
      }

      await _loadAccessibleClubs();
      if (accessibleClubs.length <= 1) {
        clubSelectionRequired = false;
      }
      final prefs = await SharedPreferences.getInstance();
      await _loadRemoteBranding(prefs);
      await refreshFromServer();
      if (pushEnabled && showPushNotifications) {
        await pushService.enable();
      }
    } catch (error) {
      // A rejected/expired token is not an offline state. Remove it completely
      // so the app returns to the login screen instead of restoring an
      // authenticated cache and entering a 401 loop.
      if (error is ApiException && error.statusCode == 401) {
        api.setToken(null);
        currentUser = null;
        accessibleClubs.clear();
        clubSelectionRequired = false;
        isAuthenticated = false;
        biometricUnlockPending = false;
        authError = null;
        _resetToNeutralBranding();
        await _secureStorage.delete(key: 'flapamamaku_token');
      } else {
        final restored = await _loadOfflineCache();
        if (restored) {
          biometricUnlockPending = false;
          authError = null;
        } else {
          api.setToken(null);
          currentUser = null;
          accessibleClubs.clear();
          clubSelectionRequired = false;
          isAuthenticated = false;
          biometricUnlockPending = false;
          _resetToNeutralBranding();
          await _secureStorage.delete(key: 'flapamamaku_token');
        }
      }
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
      biometricAvailable = await _localAuth.isDeviceSupported();
      if (!biometricAvailable) {
        biometricAvailable = await _localAuth.canCheckBiometrics;
      }
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
    accessibleClubs.clear();
    clubSelectionRequired = false;
    isAuthenticated = false;
    biometricUnlockPending = false;
    authError = null;
    _resetToNeutralBranding();
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
      authError = pushService.lastError ??
          'Push-Benachrichtigungen konnten nicht aktiviert werden.';
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
      var result = await api.login(username.trim(), password);

      final redirectUrl =
          result['server_redirect_url']?.toString().trim() ?? '';
      if (redirectUrl.isNotEmpty) {
        String trimTrailingSlash(String value) {
          var normalized = value;
          while (normalized.endsWith('/')) {
            normalized = normalized.substring(0, normalized.length - 1);
          }
          return normalized;
        }
        final normalizedRedirect = trimTrailingSlash(redirectUrl);
        final normalizedCurrent = trimTrailingSlash(api.baseUrl);
        if (normalizedRedirect != normalizedCurrent) {
          api.configureBaseUrl(normalizedRedirect);
          result = await api.login(username.trim(), password);
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString(
            'flapamamaku_server_url',
            normalizedRedirect,
          );
        }
      }

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
      accessibleClubs
        ..clear()
        ..addAll(
          (result['clubs'] as List<dynamic>? ?? const [])
              .whereType<Map>()
              .map((value) => Map<String, dynamic>.from(value)),
        );
      isAuthenticated = true;
      _pendingForcedPassword = mustChangePassword ? password : null;
      clubSelectionRequired = result['requires_club_selection'] == true;

      if (mustChangePassword) {
        clubSelectionRequired = false;
        authError = null;
        return true;
      }

      if (accessibleClubs.isEmpty) {
        await _loadAccessibleClubs();
      }
      if (accessibleClubs.length <= 1) {
        clubSelectionRequired = false;
      }
      if (!clubSelectionRequired) {
        final prefs = await SharedPreferences.getInstance();
        await _loadRemoteBranding(prefs);
        await refreshFromServer();
        if (pushEnabled && showPushNotifications) {
          await pushService.enable();
        }
      }
      return true;
    } catch (error) {
      authError = error is ApiException && error.statusCode == 401
          ? 'Benutzername oder Passwort falsch.'
          : friendlyErrorMessage(
              error,
              fallback: 'Anmeldung momentan nicht möglich. Bitte nochmals versuchen.',
            );
      isAuthenticated = false;
      currentUser = null;
      _pendingForcedPassword = null;
      accessibleClubs.clear();
      clubSelectionRequired = false;
      _resetToNeutralBranding();
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
    _pendingForcedPassword = null;
    accessibleClubs.clear();
    clubSelectionRequired = false;
    isAuthenticated = false;
    biometricUnlockPending = false;
    authError = null;
    _resetToNeutralBranding();
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
    if (!api.isConfigured ||
        !isAuthenticated ||
        mustChangePassword ||
        isSyncing) {
      return;
    }

    isSyncing = true;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      await _loadRemoteBranding(prefs);

      final remoteNews =
          showNews ? await api.fetchNews() : <NewsItem>[];
      final remoteEvents =
          showEvents ? await api.fetchEvents() : <EventItem>[];
      final remoteMembers =
          showMembers ? await api.fetchMembers() : <MemberItem>[];
      final remoteMemberFilters =
          showMembers ? await api.fetchMemberFilters() : <MemberFilterItem>[];
      final remoteContent = await api.fetchContent();
      final remotePolls =
          showPolls ? await api.fetchPolls() : <ContentItem>[];

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
        ..addAll(
          remoteContent.where((item) {
            switch (item.section) {
              case 'gallery':
                return showGallery;
              case 'sujet':
                return showSujet;
              case 'archive':
                return showArchive;
              case 'photos':
                return showPhotos;
              case 'documents':
                return showDocuments;
              case 'links':
              case 'whatsapp':
                return showLinks;
              case 'polls':
                return showPolls;
              default:
                return true;
            }
          }),
        )
        ..addAll(remotePolls);

      _sortNews();
      _sortEvents();
      isUsingServer = true;
      syncError = null;
      lastSuccessfulSync = DateTime.now();
      await _saveOfflineCache();
    } catch (error) {
      isUsingServer = false;
      syncError = friendlyErrorMessage(error);
      if (news.isEmpty && events.isEmpty && members.isEmpty && content.isEmpty) {
        await _loadOfflineCache();
      }
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
        syncError = friendlyErrorMessage(error);
        notifyListeners();
        rethrow;
      }
      return;
    }
    if (item.id == null) return;
    try {
      if (item.section == 'polls') {
        await api.deletePoll(item.id!);
      } else {
        await api.deleteContent(item.id!);
      }
      await refreshFromServer();
    } catch (error) {
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
      syncError = friendlyErrorMessage(error);
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
