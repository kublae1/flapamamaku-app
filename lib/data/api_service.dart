import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/app_data.dart';

class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = (baseUrl ??
                const String.fromEnvironment(
                  'API_BASE_URL',
                  defaultValue: '',
                ))
            .replaceAll(RegExp(r'/+$'), '');

  final String baseUrl;

  bool get isConfigured => baseUrl.isNotEmpty;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<List<NewsItem>> fetchNews() async {
    final response = await http
        .get(_uri('/api/news'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => NewsItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  Future<List<EventItem>> fetchEvents() async {
    final response = await http
        .get(_uri('/api/events'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => EventItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  Future<List<MemberItem>> fetchMembers() async {
    final response = await http
        .get(_uri('/api/members'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => MemberItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  void _ensureSuccess(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        'HTTP ${response.statusCode}: ${response.body}',
      );
    }
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}
