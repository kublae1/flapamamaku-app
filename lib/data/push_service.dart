import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'api_service.dart';

class PushService {
  PushService(this.api);

  final ApiService api;
  StreamSubscription<String>? _tokenSubscription;
  String? _registeredToken;
  bool _initialized = false;

  static const _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const _appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const _senderId = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  static const _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');

  bool get isConfigured =>
      _apiKey.isNotEmpty &&
      _appId.isNotEmpty &&
      _senderId.isNotEmpty &&
      _projectId.isNotEmpty;

  Future<bool> enable() async {
    if (!isConfigured || !api.isConfigured || !api.hasToken) return false;

    try {
      if (!_initialized) {
        await Firebase.initializeApp(
          options: const FirebaseOptions(
            apiKey: _apiKey,
            appId: _appId,
            messagingSenderId: _senderId,
            projectId: _projectId,
          ),
        );
        _initialized = true;
      }

      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        return false;
      }

      final token = await messaging.getToken();
      if (token == null || token.isEmpty) return false;
      await _register(token);

      await _tokenSubscription?.cancel();
      _tokenSubscription = messaging.onTokenRefresh.listen((newToken) async {
        try {
          await _register(newToken);
        } catch (_) {}
      });
      return true;
    } catch (_) {
      return false;
    }
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
  }
}
