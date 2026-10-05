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
      : _baseUrl = _normalizeBaseUrl(
          baseUrl ??
              const String.fromEnvironment(
                'API_BASE_URL',
                defaultValue: '',
              ),
        );

  static const expectedInstanceId = String.fromEnvironment(
    'CLUB_INSTANCE_ID',
    defaultValue: 'flapamamaku',
  );

  String _baseUrl;
  String get baseUrl => _baseUrl;

  static String _normalizeBaseUrl(String value) {
    var result = value.trim();
    while (result.endsWith('/')) {
      result = result.substring(0, result.length - 1);
    }
    return result;
  }

  void configureBaseUrl(String value) {
    _baseUrl = _normalizeBaseUrl(value);
    setToken(null);
  }
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

  Future<List<Map<String, dynamic>>> fetchAccessibleClubs() async {
    final response = await http
        .get(_uri('/api/clubs/accessible'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) => Map<String, dynamic>.from(value as Map))
        .toList();
  }

  Future<Map<String, dynamic>> switchClub(int clubId) async {
    final response = await http
        .post(
          _uri('/api/auth/club'),
          headers: _jsonHeaders,
          body: jsonEncode({'club_id': clubId}),
        )
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

  Map<String, dynamic> _prepareContentJson(Map<String, dynamic> json) {
    String absolute(String value) =>
        value.startsWith('/') ? '$baseUrl$value' : value;

    final images = (json['images'] as List<dynamic>? ?? const [])
        .map((value) => Map<String, dynamic>.from(value as Map))
        .map((image) {
          final url = image['url']?.toString() ?? '';
          image['url'] = absolute(url);
          return image;
        })
        .toList();
    json['images'] = images;

    final imageUrls = (json['image_urls'] as List<dynamic>? ?? const [])
        .map((value) => absolute(value.toString()))
        .toList();
    json['image_urls'] = imageUrls;

    final imageUrl = json['image_url']?.toString() ?? '';
    json['image_url'] = absolute(imageUrl);

    final documentUrl = json['document_url']?.toString() ?? '';
    json['document_url'] = absolute(documentUrl);
    return json;
  }

  Future<Map<String, dynamic>> fetchAppConfig() async {
    final response = await http
        .get(_uri('/api/app-config'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final serverInstanceId =
        json['instance_id']?.toString().trim().toLowerCase() ?? '';
    final expected = expectedInstanceId.trim().toLowerCase();
    if (serverInstanceId.isEmpty) {
      throw const ApiException(
        'Der Vereinsserver hat keine gültige Instanz-ID.',
        statusCode: 409,
      );
    }
    if (expected.isNotEmpty && serverInstanceId != expected) {
      throw ApiException(
        'Dieser Server gehört zu einem anderen Verein '
        '(erwartet: $expected, gefunden: $serverInstanceId).',
        statusCode: 409,
      );
    }

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

  Future<List<ContentItem>> fetchPolls() async {
    final response = await http
        .get(_uri('/api/polls'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values.map((value) {
      final json = _prepareContentJson(
        Map<String, dynamic>.from(value as Map<String, dynamic>),
      );
      return ContentItem.fromJson(json);
    }).toList();
  }

  Future<ContentItem> savePoll(ContentItem item) async {
    final body = jsonEncode({
      'title': item.title,
      'text': item.text,
      'options': item.pollOptions,
      'allow_suggestions': item.pollAllowSuggestions,
    });
    final response = item.id == null
        ? await http
            .post(_uri('/api/polls'), headers: _jsonHeaders, body: body)
            .timeout(const Duration(seconds: 8))
        : await http
            .put(
              _uri('/api/polls/${item.id}'),
              headers: _jsonHeaders,
              body: body,
            )
            .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final json = _prepareContentJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
    return ContentItem.fromJson(json);
  }

  Future<void> deletePoll(int pollId) async {
    final response = await http
        .delete(_uri('/api/polls/$pollId'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
  }

  Future<List<ContentItem>> fetchContent({String? section}) async {
    if (section == 'polls') {
      return fetchPolls();
    }
    final suffix = section == null || section.isEmpty
        ? ''
        : '?section=${Uri.encodeQueryComponent(section)}';
    final response = await http
        .get(_uri('/api/content$suffix'), headers: authHeaders)
        .timeout(const Duration(seconds: 8));
    _ensureSuccess(response);
    final values = jsonDecode(response.body) as List<dynamic>;
    return values
        .map((value) {
          final json = _prepareContentJson(
            Map<String, dynamic>.from(value as Map<String, dynamic>),
          );
          return ContentItem.fromJson(json);
        })
        .where((item) => section != null || item.section != 'polls')
        .toList();
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
    final json = _prepareContentJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
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
    final json = _prepareContentJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
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
    if (response.statusCode >= 200 && response.statusCode < 300) return;

    String? detail;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map) {
        detail = decoded['detail']?.toString().trim();
      }
    } catch (_) {
      // Never expose raw server or HTML error bodies to the app UI.
    }

    throw ApiException(
      _messageForStatus(response.statusCode, detail),
      statusCode: response.statusCode,
    );
  }

  String _messageForStatus(int statusCode, String? detail) {
    switch (statusCode) {
      case 400:
        return detail?.isNotEmpty == true
            ? detail!
            : 'Die Eingabe konnte nicht verarbeitet werden.';
      case 401:
        return 'Die Anmeldung ist nicht mehr gültig. Bitte erneut anmelden.';
      case 403:
        return 'Für diese Aktion fehlt die Berechtigung.';
      case 404:
        return 'Der gewünschte Inhalt wurde nicht gefunden.';
      case 409:
        return detail?.isNotEmpty == true
            ? detail!
            : 'Die Änderung steht im Konflikt mit bereits vorhandenen Daten.';
      case 413:
        return 'Die Datei ist zu gross.';
      case 422:
        return detail?.isNotEmpty == true
            ? detail!
            : 'Bitte die eingegebenen Daten prüfen.';
      case 429:
        return 'Zu viele Anfragen. Bitte kurz warten und nochmals versuchen.';
      default:
        if (statusCode >= 500) {
          return 'Der Server hat momentan ein Problem. Bitte später nochmals versuchen.';
        }
        return 'Die Anfrage konnte nicht abgeschlossen werden.';
    }
  }
}

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

String friendlyErrorMessage(
  Object error, {
  String fallback = 'Die Aktion konnte nicht abgeschlossen werden.',
}) {
  if (error is ApiException) return error.message;

  final text = error.toString().toLowerCase();
  if (text.contains('timeout') || text.contains('timed out')) {
    return 'Der Server antwortet nicht. Bitte Verbindung prüfen und nochmals versuchen.';
  }
  if (text.contains('socketexception') ||
      text.contains('clientexception') ||
      text.contains('failed host lookup') ||
      text.contains('connection refused') ||
      text.contains('connection closed') ||
      text.contains('network is unreachable') ||
      text.contains('no address associated with hostname')) {
    return 'Keine Verbindung zum Server. Bitte Internetverbindung prüfen.';
  }
  if (error is FormatException || text.contains('formatexception')) {
    return 'Der Server hat eine ungültige Antwort geliefert.';
  }

  return fallback;
}
