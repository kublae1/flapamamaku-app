import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/data/runtime_content_policy.dart';

void main() {
  group('Phase-1 bundled content policy', () {
    test('local development without server may use bundled demo data', () {
      expect(allowBundledDemoContent(serverConfigured: false), isTrue);
    });

    test('configured club server must never use bundled demo data', () {
      expect(allowBundledDemoContent(serverConfigured: true), isFalse);
    });
  });
}
