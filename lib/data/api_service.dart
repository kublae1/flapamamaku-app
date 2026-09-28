import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../models/app_data.dart';

class DownloadedImage {
  final Uint8List bytes;
  final String mimeType;

  const DownloadedImage({
    required this.bytes,
    required this.mimeType,
  });
}

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

  Future<Map<String, dynamic>> fetchAppConfig() async {
    final response = await http
        .get(_uri('/api/app-config'))
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final logoUrl = json['logo_url']?.toString() ?? '';
    if (logoUrl.startsWith('/')) {
      json['logo_url'] = '$baseUrl$logoUrl';
    }
    return json;
  }

  Future<DownloadedImage> downloadImage(String url) async {
    final response = await http
        .get(Uri.parse(url), headers: authHeaders)
        .timeout(const Duration(seconds: 20));
    _ensureSuccess(response);
    return DownloadedImage(
      bytes: response.bodyBytes,
      mimeType: response.headers['content-type']?.split(';').first.trim() ??
          'image/jpeg',
    );
  }

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

  Future<List<MemberFilterItem>> fetchMemberFilters() async {
    final response = await http
        .get(_uri('/api/member-filters'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => MemberFilterItem.fromJson(value as Map<String, dynamic>))
        .toList();
  }

  Future<List<MemberItem>> fetchMembers() async {
    final response = await http
        .get(_uri('/api/members'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values.map((value) {
      final json = Map<String, dynamic>.from(
        value as Map<String, dynamic>,
      );
      final photoUrl = json['photo_url']?.toString() ?? '';
      if (photoUrl.startsWith('/')) {
        json['photo_url'] = '$baseUrl$photoUrl';
      }
      return MemberItem.fromJson(json);
    }).toList();
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
      final imageUrls = (json['image_urls'] as List<dynamic>? ?? const [])
          .map((value) => value.toString())
          .map((value) => value.startsWith('/') ? '$baseUrl$value' : value)
          .toList();
      json['image_urls'] = imageUrls;
      final imageUrl = json['image_url']?.toString() ?? '';
      if (imageUrl.startsWith('/')) {
        json['image_url'] = '$baseUrl$imageUrl';
      }
      final documentUrl = json['document_url']?.toString() ?? '';
      if (documentUrl.startsWith('/')) {
        json['document_url'] = '$baseUrl$documentUrl';
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
      'poll_options': item.pollOptions,
      'poll_allow_suggestions': item.pollAllowSuggestions,
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
    final imageUrls = (json['image_urls'] as List<dynamic>? ?? const [])
        .map((value) => value.toString())
        .map((value) => value.startsWith('/') ? '$baseUrl$value' : value)
        .toList();
    json['image_urls'] = imageUrls;
    final imageUrl = json['image_url']?.toString() ?? '';
    if (imageUrl.startsWith('/')) {
      json['image_url'] = '$baseUrl$imageUrl';
    }
    final documentUrl = json['document_url']?.toString() ?? '';
    if (documentUrl.startsWith('/')) {
      json['document_url'] = '$baseUrl$documentUrl';
    }
    return ContentItem.fromJson(json);
  }

  Future<Uint8List> downloadDocument(String url) async {
    final response = await http
        .get(Uri.parse(url), headers: authHeaders)
        .timeout(const Duration(seconds: 30));
    _ensureSuccess(response);
    return response.bodyBytes;
  }

  Future<ContentItem> votePoll(int pollId, int optionIndex) async {
    final response = await http
        .post(
          _uri('/api/polls/$pollId/vote'),
          headers: _jsonHeaders,
          body: jsonEncode({'option_index': optionIndex}),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ContentItem.fromJson(json);
  }

  Future<ContentItem> suggestAndVotePoll(int pollId, String text) async {
    final response = await http
        .post(
          _uri('/api/polls/$pollId/suggest-and-vote'),
          headers: _jsonHeaders,
          body: jsonEncode({'text': text.trim()}),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ContentItem.fromJson(json);
  }

  Future<void> deleteContentImage(int contentId, int imageId) async {
    final response = await http
        .delete(
          _uri('/api/content/$contentId/images/$imageId'),
          headers: authHeaders,
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<void> deleteContent(int id) async {
    final response = await http
        .delete(_uri('/api/content/$id'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<void> registerPushToken({
    required String token,
    required String platform,
  }) async {
    final response = await http
        .post(
          _uri('/api/push/register'),
          headers: _jsonHeaders,
          body: jsonEncode({'token': token, 'platform': platform}),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<void> unregisterPushToken(String token) async {
    final response = await http
        .delete(
          _uri('/api/push/register'),
          headers: _jsonHeaders,
          body: jsonEncode({'token': token}),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<ContentItem> uploadGallerySnapshot({
    required Uint8List bytes,
    required String filename,
    required int expiresDays,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      _uri('/api/gallery/snapshots?expires_days=$expiresDays'),
    );
    request.headers.addAll(authHeaders);
    final lowerName = filename.toLowerCase();
    final mediaType = lowerName.endsWith('.png')
        ? MediaType('image', 'png')
        : lowerName.endsWith('.webp')
            ? MediaType('image', 'webp')
            : MediaType('image', 'jpeg');

    request.files.add(
      http.MultipartFile.fromBytes(
        'image',
        bytes,
        filename: filename.isEmpty ? 'snapshot.jpg' : filename,
        contentType: mediaType,
      ),
    );
    final streamed = await request.send().timeout(const Duration(seconds: 30));
    final response = await http.Response.fromStream(streamed);
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final imageUrls = (json['image_urls'] as List<dynamic>? ?? const [])
        .map((value) => value.toString())
        .map((value) => value.startsWith('/') ? '$baseUrl$value' : value)
        .toList();
    json['image_urls'] = imageUrls;
    final imageUrl = json['image_url']?.toString() ?? '';
    if (imageUrl.startsWith('/')) {
      json['image_url'] = '$baseUrl$imageUrl';
    }
    return ContentItem.fromJson(json);
  }

  Future<void> deleteGallerySnapshot(int snapshotId) async {
    final response = await http
        .delete(
          _uri('/api/gallery/snapshots/$snapshotId'),
          headers: authHeaders,
        )
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

  Future<List<String>> fetchEventRegistrations(int eventId) async {
    final response = await http
        .get(_uri('/api/events/$eventId/registrations'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => (value as Map<String, dynamic>)['name']?.toString() ?? '')
        .where((name) => name.isNotEmpty)
        .toList();
  }

  Future<void> setEventRegistration(int eventId, bool registered) async {
    final response = registered
        ? await http
            .post(_uri('/api/events/$eventId/registration'), headers: authHeaders)
            .timeout(const Duration(seconds: 8))
        : await http
            .delete(_uri('/api/events/$eventId/registration'), headers: authHeaders)
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
      'birth_date': item.birthDate,
      'status': item.status,
      'member_group': item.memberGroup,
      'engagement': item.engagement,
      'filter_ids': item.filterIds,
      'partner_name': item.partnerName,
      'phone_mobile': item.phoneMobile,
      'phone_private': item.phonePrivate,
      'phone_work': item.phoneWork,
      'email': item.email,
      'address': item.address,
      'occupation': item.occupation,
      'employer': item.employer,
      'employer_url': item.employerUrl,
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
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final photoUrl = json['photo_url']?.toString() ?? '';
    if (photoUrl.startsWith('/')) {
      json['photo_url'] = '$baseUrl$photoUrl';
    }
    return MemberItem.fromJson(json);
  }

  Future<MemberItem> updateOwnMember(MemberItem item) async {
    final response = await http
        .put(
          _uri('/api/members/me'),
          headers: _jsonHeaders,
          body: jsonEncode({
            'partner_name': item.partnerName,
            'phone_mobile': item.phoneMobile,
            'phone_private': item.phonePrivate,
            'phone_work': item.phoneWork,
            'email': item.email,
            'address': item.address,
            'occupation': item.occupation,
            'employer': item.employer,
            'employer_url': item.employerUrl,
            'engagement': item.engagement,
          }),
        )
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final photoUrl = json['photo_url']?.toString() ?? '';
    if (photoUrl.startsWith('/')) {
      json['photo_url'] = '$baseUrl$photoUrl';
    }
    return MemberItem.fromJson(json);
  }

  Future<MemberItem> uploadOwnMemberPhoto({
    required Uint8List bytes,
    required String filename,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      _uri('/api/members/me/photo'),
    );
    request.headers.addAll(authHeaders);
    final lowerName = filename.toLowerCase();
    final mediaType = lowerName.endsWith('.png')
        ? MediaType('image', 'png')
        : lowerName.endsWith('.webp')
            ? MediaType('image', 'webp')
            : MediaType('image', 'jpeg');
    request.files.add(
      http.MultipartFile.fromBytes(
        'photo',
        bytes,
        filename: filename.isEmpty ? 'mitglied.jpg' : filename,
        contentType: mediaType,
      ),
    );
    final streamed = await request.send().timeout(const Duration(seconds: 30));
    final response = await http.Response.fromStream(streamed);
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final photoUrl = json['photo_url']?.toString() ?? '';
    if (photoUrl.startsWith('/')) {
      json['photo_url'] = '$baseUrl$photoUrl';
    }
    return MemberItem.fromJson(json);
  }

  Future<void> deleteOwnMemberPhoto() async {
    final response = await http
        .delete(_uri('/api/members/me/photo'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
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
