import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ClubMessage {
  final int id;
  final String kind;
  final String title;
  final String body;
  final String route;
  final DateTime? createdAt;
  final bool read;
  final bool urgent;

  const ClubMessage({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.route,
    required this.createdAt,
    required this.read,
    required this.urgent,
  });

  factory ClubMessage.fromJson(Map<String, dynamic> json) => ClubMessage(
        id: json['id'] is int
            ? json['id'] as int
            : int.tryParse(json['id']?.toString() ?? '') ?? 0,
        kind: json['kind']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        body: json['body']?.toString() ?? '',
        route: json['route']?.toString() ?? '',
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? ''),
        read: json['read'] == true,
        urgent: json['urgent'] == true,
      );
}

class MessageApi {
  final ApiService api;
  const MessageApi(this.api);

  Uri _uri(String path) => Uri.parse('${api.baseUrl}$path');

  void _ensureSuccess(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) return;
    String message = 'Mitteilungen konnten nicht verarbeitet werden.';
    try {
      final value = jsonDecode(response.body);
      if (value is Map && value['detail']?.toString().trim().isNotEmpty == true) {
        message = value['detail'].toString().trim();
      }
    } catch (_) {}
    throw ApiException(message, statusCode: response.statusCode);
  }

  Future<List<ClubMessage>> fetchMessages() async {
    final response = await http
        .get(_uri('/api/messages'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final rows = jsonDecode(response.body) as List<dynamic>;
    return rows
        .whereType<Map>()
        .map((row) => ClubMessage.fromJson(Map<String, dynamic>.from(row)))
        .toList();
  }

  Future<int> unreadCount() async {
    final response = await http
        .get(_uri('/api/messages/unread-count'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final value = jsonDecode(response.body) as Map<String, dynamic>;
    return value['unread'] is int
        ? value['unread'] as int
        : int.tryParse(value['unread']?.toString() ?? '') ?? 0;
  }

  Future<void> markRead(int messageId) async {
    final response = await http
        .post(
          _uri('/api/messages/$messageId/read'),
          headers: api.authHeaders,
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<void> markAllRead() async {
    final response = await http
        .post(_uri('/api/messages/read-all'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<void> deleteMessage(int messageId) async {
    final response = await http
        .delete(_uri('/api/messages/$messageId'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<int> deleteReadMessages() async {
    final response = await http
        .delete(_uri('/api/messages/read'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final value = jsonDecode(response.body) as Map<String, dynamic>;
    return value['deleted'] is int
        ? value['deleted'] as int
        : int.tryParse(value['deleted']?.toString() ?? '') ?? 0;
  }

  Future<int> deleteAllMessages() async {
    final response = await http
        .delete(_uri('/api/messages'), headers: api.authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final value = jsonDecode(response.body) as Map<String, dynamic>;
    return value['deleted'] is int
        ? value['deleted'] as int
        : int.tryParse(value['deleted']?.toString() ?? '') ?? 0;
  }

  Future<void> sendMessage({
    required String title,
    required String body,
    required bool urgent,
    String route = '/messages',
  }) async {
    final response = await http
        .post(
          _uri('/api/push/admin/send-v2'),
          headers: {
            'Content-Type': 'application/json',
            ...api.authHeaders,
          },
          body: jsonEncode({
            'title': title,
            'body': body,
            'route': route,
            'urgency': urgent ? 'urgent' : 'normal',
          }),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }
}
