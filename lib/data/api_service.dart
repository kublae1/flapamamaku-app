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

  Map<String, String> get _jsonHeaders => const {
        'Content-Type': 'application/json',
      };

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

  Future<NewsItem> saveNews(NewsItem item) async {
    final body = jsonEncode({
      'title': item.title,
      'text': item.text,
      'date': item.date,
      'image_url': item.imageUrl,
    });
    final response = item.id == null
        ? await http
            .post(_uri('/api/news'), headers: _jsonHeaders, body: body)
            .timeout(const Duration(seconds: 8))
        : await http
            .put(
              _uri('/api/news/${item.id}'),
              headers: _jsonHeaders,
              body: body,
            )
            .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    return NewsItem.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> deleteNews(int id) async {
    final response = await http
        .delete(_uri('/api/news/$id'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<EventItem> saveEvent(EventItem item) async {
    final body = jsonEncode({
      'event_date': item.eventDate,
      'day': item.day,
      'month': item.month,
      'title': item.title,
      'location': item.location,
      'time': item.time,
    });
    final response = item.id == null
        ? await http
            .post(_uri('/api/events'), headers: _jsonHeaders, body: body)
            .timeout(const Duration(seconds: 8))
        : await http
            .put(
              _uri('/api/events/${item.id}'),
              headers: _jsonHeaders,
              body: body,
            )
            .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    return EventItem.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> deleteEvent(int id) async {
    final response = await http
        .delete(_uri('/api/events/$id'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<MemberItem> saveMember(MemberItem item) async {
    final body = jsonEncode({
      'name': item.name,
      'role': item.role,
      'since': item.since,
      'partner_name': item.partnerName,
      'phone_mobile': item.phoneMobile,
      'phone_private': item.phonePrivate,
      'phone_work': item.phoneWork,
      'email': item.email,
      'address': item.address,
      'occupation': item.occupation,
      'employer': item.employer,
    });
    final response = item.id == null
        ? await http
            .post(_uri('/api/members'), headers: _jsonHeaders, body: body)
            .timeout(const Duration(seconds: 8))
        : await http
            .put(
              _uri('/api/members/${item.id}'),
              headers: _jsonHeaders,
              body: body,
            )
            .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    return MemberItem.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> deleteMember(int id) async {
    final response = await http
        .delete(_uri('/api/members/$id'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
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
