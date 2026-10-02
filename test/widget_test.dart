import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flapamamaku_app/data/api_service.dart';
import 'package:flapamamaku_app/data/app_store.dart';
import 'package:flapamamaku_app/screens/login_screen.dart';

void main() {
  testWidgets('login offers club server setup when no server is configured',
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
    expect(find.text('Vereinsserver'), findsOneWidget);
    expect(find.text('Vereinsserver einrichten'), findsNothing);

    await tester.tap(find.text('Vereinsserver'));
    await tester.pumpAndSettle();

    expect(find.text('Vereinsserver einrichten'), findsOneWidget);

    store.dispose();
  });
}
