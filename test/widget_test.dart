import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flapamamaku_app/data/api_service.dart';
import 'package:flapamamaku_app/data/app_store.dart';
import 'package:flapamamaku_app/screens/login_screen.dart';

void main() {
  testWidgets('login stays neutral and hides server administration',
      (tester) async {
    final store = AppStore(api: ApiService(baseUrl: ''));
    store.authReady = true;
    store.isAuthenticated = false;

    await tester.pumpWidget(
      AppStoreScope(
        store: store,
        child: MaterialApp(
          home: const LoginScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Vereins-App'), findsOneWidget);
    expect(find.text('Anmelden'), findsWidgets);
    expect(find.textContaining('Vereinsserver'), findsNothing);

    store.dispose();
  });
}
