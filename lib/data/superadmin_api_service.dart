import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

/// Keeps the normal app login flow for every club account, but permits the
/// platform Superadmin to use the mobile app as well.
///
/// Older backend releases deliberately reject `client=app` for Superadmin with
/// HTTP 403. In that one case we retry the same credentials as the already
/// supported admin client. The returned session still contains the active club
/// and accessible-club list, so the existing tenant isolation and club switch
/// continue to apply unchanged.
class SuperAdminApiService extends ApiService {
  SuperAdminApiService({super.baseUrl});

  @override
  Future<Map<String, dynamic>> login(
    String username,
    String password,
  ) async {
    try {
      return await super.login(username, password);
    } on ApiException catch (error) {
      if (error.statusCode != 403) rethrow;

      final response = await http
          .post(
            Uri.parse('$baseUrl/api/auth/login'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'username': username,
              'password': password,
              'client': 'admin',
            }),
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode < 200 || response.statusCode >= 300) {
        String message = 'Anmeldung momentan nicht möglich. Bitte nochmals versuchen.';
        try {
          final decoded = jsonDecode(response.body);
          if (decoded is Map && decoded['detail']?.toString().trim().isNotEmpty == true) {
            message = decoded['detail'].toString().trim();
          }
        } catch (_) {}
        throw ApiException(message, statusCode: response.statusCode);
      }

      final result = jsonDecode(response.body) as Map<String, dynamic>;
      final token = result['token']?.toString() ?? '';
      if (token.isEmpty) {
        throw const ApiException('Kein Sitzungstoken erhalten.');
      }
      setToken(token);
      return result;
    }
  }
}
