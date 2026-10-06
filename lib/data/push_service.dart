import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'api_service.dart';

class PushService {
  PushService(this.api);

  final ApiService api;
  StreamSubscription<String>? _tokenSubscription;
  StreamSubscription<RemoteMessage>? _openedSubscription;
  StreamSubscription<RemoteMessage>? _foregroundSubscription;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  String? _registeredToken;
  String? _pendingRoute;
  bool _initialized = false;
  String? lastError;
  void Function(String route)? onRoute;

  static const _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const _appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const _senderId = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  static const _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const _appName = String.fromEnvironment(
    'APP_NAME',
    defaultValue: 'FLAPAMAMAKU',
  );

  bool get isConfigured =>
      _apiKey.isNotEmpty &&
      _appId.isNotEmpty &&
      _senderId.isNotEmpty &&
      _projectId.isNotEmpty;

  Future<bool> enable() async {
    lastError = null;
    if (!isConfigured) {
      lastError = 'Firebase-Konfiguration fehlt in diesem App-Build.';
      return false;
    }
    if (!api.isConfigured) {
      lastError = 'Der Vereinsserver ist nicht konfiguriert.';
      return false;
    }
    if (!api.hasToken) {
      lastError = 'Für Push ist zuerst eine gültige Anmeldung erforderlich.';
      return false;
    }

    try {
      if (!_initialized) {
        if (Firebase.apps.isEmpty) {
          await Firebase.initializeApp(
            options: const FirebaseOptions(
              apiKey: _apiKey,
              appId: _appId,
              messagingSenderId: _senderId,
              projectId: _projectId,
            ),
          );
        }
        const androidSettings =
            AndroidInitializationSettings('ic_stat_flapamamaku');
        const darwinSettings = DarwinInitializationSettings();
        const initializationSettings = InitializationSettings(
          android: androidSettings,
          iOS: darwinSettings,
        );
        await _localNotifications.initialize(
          initializationSettings,
          onDidReceiveNotificationResponse: (response) {
            final route = response.payload ?? '';
            if (route.isNotEmpty) _dispatchRoute(route);
          },
        );

        if (Platform.isAndroid) {
          final channel = AndroidNotificationChannel(
            'flapamamaku_push',
            '$_appName Benachrichtigungen',
            description: 'News, Termine und neue Vereinsinhalte',
            importance: Importance.high,
          );
          await _localNotifications
              .resolvePlatformSpecificImplementation<
                  AndroidFlutterLocalNotificationsPlugin>()
              ?.createNotificationChannel(channel);
        }

        _initialized = true;
      }

      final messaging = FirebaseMessaging.instance;
      await messaging.setAutoInitEnabled(true);
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        lastError = 'Die Android-Berechtigung für Benachrichtigungen wurde abgelehnt.';
        return false;
      }

      final token = await messaging.getToken();
      if (token == null || token.isEmpty) {
        lastError = 'Firebase hat kein Geräte-Token geliefert.';
        return false;
      }
      await _register(token);

      final initialMessage = await messaging.getInitialMessage();
      final initialRoute = initialMessage?.data['route']?.toString() ?? '';
      if (initialRoute.isNotEmpty) {
        _dispatchRoute(initialRoute);
      }

      await _openedSubscription?.cancel();
      _openedSubscription = FirebaseMessaging.onMessageOpenedApp.listen((message) {
        final route = message.data['route']?.toString() ?? '';
        if (route.isNotEmpty) {
          _dispatchRoute(route);
        }
      });

      await _foregroundSubscription?.cancel();
      _foregroundSubscription = FirebaseMessaging.onMessage.listen((message) async {
        final title = message.notification?.title ??
            message.data['title']?.toString() ??
            _appName;
        final body = message.notification?.body ??
            message.data['body']?.toString() ??
            '';
        final route = message.data['route']?.toString() ?? '';

        final androidDetails = AndroidNotificationDetails(
          'flapamamaku_push',
          '$_appName Benachrichtigungen',
          channelDescription: 'News, Termine und neue Vereinsinhalte',
          importance: Importance.high,
          priority: Priority.high,
          icon: 'ic_stat_flapamamaku',
          largeIcon: const DrawableResourceAndroidBitmap('ic_launcher'),
        );
        const darwinDetails = DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        );
        final details = NotificationDetails(
          android: Platform.isAndroid ? androidDetails : null,
          iOS: Platform.isIOS ? darwinDetails : null,
        );
        await _localNotifications.show(
          message.messageId?.hashCode ?? DateTime.now().millisecondsSinceEpoch,
          title,
          body,
          details,
          payload: route,
        );
      });

      await _tokenSubscription?.cancel();
      _tokenSubscription = messaging.onTokenRefresh.listen((newToken) async {
        try {
          await _register(newToken);
        } catch (_) {}
      });
      lastError = null;
      return true;
    } catch (error) {
      lastError = 'Push-Initialisierung fehlgeschlagen: $error';
      return false;
    }
  }

  void _dispatchRoute(String route) {
    final handler = onRoute;
    if (handler != null) {
      handler(route);
    } else {
      _pendingRoute = route;
    }
  }

  String? takePendingRoute() {
    final route = _pendingRoute;
    _pendingRoute = null;
    return route;
  }

  Future<void> _register(String token) async {
    await api.registerPushToken(
      token: token,
      platform: Platform.isIOS ? 'ios' : 'android',
    );
    _registeredToken = token;
  }

  Future<void> disable() async {
    await _tokenSubscription?.cancel();
    _tokenSubscription = null;
    await _openedSubscription?.cancel();
    _openedSubscription = null;
    await _foregroundSubscription?.cancel();
    _foregroundSubscription = null;

    final token = _registeredToken;
    _registeredToken = null;
    if (token == null || token.isEmpty || !api.hasToken) return;

    try {
      await api.unregisterPushToken(token);
    } catch (_) {}
  }

  Future<void> dispose() async {
    await _tokenSubscription?.cancel();
    _tokenSubscription = null;
    await _openedSubscription?.cancel();
    _openedSubscription = null;
    await _foregroundSubscription?.cancel();
    _foregroundSubscription = null;
  }
}
