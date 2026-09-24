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
  String? _token;

  bool get isConfigured => baseUrl.isNotEmpty;
  bool get hasToken => _token?.isNotEmpty == true;

  void setToken(String? token) {
    _token = token?.trim().isEmpty == true ? null : token?.trim();
  }

  Map<String, String> get authHeaders => {
        if (hasToken) 'Authorization': 'Bearer $_token',
      };

  Map<String, String> get _jsonHeaders => {
        'Content-Type': 'application/json',
        ...authHeaders,
      };

  Future<Map<String, dynamic>> login(
    String username,
    String password,
  ) async {
    final response = await http
        .post(
          _uri('/api/auth/login'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final token = json['token']?.toString() ?? '';
    setToken(token);
    return json;
  }

  Future<Map<String, dynamic>> fetchMe() async {
    final response = await http
        .get(_uri('/api/auth/me'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<void> logout() async {
    if (!hasToken) return;
    final response = await http
        .post(_uri('/api/auth/logout'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    if (response.statusCode != 401) {
      _ensureSuccess(response);
    }
    setToken(null);
  }

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<List<NewsItem>> fetchNews() async {
    final response = await http
        .get(_uri('/api/news'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values.map((value) {
      final json = Map<String, dynamic>.from(
        value as Map<String, dynamic>,
      );
      final imageUrl = json['image_url']?.toString() ?? '';
      if (imageUrl.startsWith('/')) {
        json['image_url'] = '$baseUrl$imageUrl';
      }
      return NewsItem.fromJson(json);
    }).toList();
  }

  Future<List<EventItem>> fetchEvents() async {
    final response = await http
        .get(_uri('/api/events'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => EventItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  Future<List<MemberItem>> fetchMembers() async {
    final response = await http
        .get(_uri('/api/members'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => MemberItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  Future<List<ContentItem>> fetchContent({String? section}) async {
    final suffix = section == null || section.isEmpty
        ? ''
        : '?section=${Uri.encodeQueryComponent(section)}';
    final response = await http
        .get(_uri('/api/content$suffix'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values.map((value) {
      final json = Map<String, dynamic>.from(
        value as Map<String, dynamic>,
      );
      final imageUrl = json['image_url']?.toString() ?? '';
      if (imageUrl.startsWith('/')) {
        json['image_url'] = '$baseUrl$imageUrl';
      }
      return ContentItem.fromJson(json);
    }).toList();
  }

  Future<ContentItem> saveContent(ContentItem item) async {
    final body = jsonEncode({
      'section': item.section,
      'title': item.title,
      'text': item.text,
      'link_url': item.linkUrl,
    });
    final response = item.id == null
        ? await http
            .post(_uri('/api/content'), headers: _jsonHeaders, body: body)
            .timeout(const Duration(seconds: 8))
        : await http
            .put(
              _uri('/api/content/${item.id}'),
              headers: _jsonHeaders,
              body: body,
            )
            .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final imageUrl = json['image_url']?.toString() ?? '';
    if (imageUrl.startsWith('/')) {
      json['image_url'] = '$baseUrl$imageUrl';
    }
    return ContentItem.fromJson(json);
  }

  Future<void> deleteContent(int id) async {
    final response = await http
        .delete(_uri('/api/content/$id'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
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
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final imageUrl = json['image_url']?.toString() ?? '';
    if (imageUrl.startsWith('/')) {
      json['image_url'] = '$baseUrl$imageUrl';
    }
    return NewsItem.fromJson(json);
  }

  Future<void> deleteNews(int id) async {
    final response = await http
        .delete(_uri('/api/news/$id'), headers: authHeaders)
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
        .delete(_uri('/api/events/$id'), headers: authHeaders)
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
        .delete(_uri('/api/members/$id'), headers: authHeaders)
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
