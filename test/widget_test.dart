import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/main.dart';

void main() {
  testWidgets('login and server setup are available without a configured server',
      (tester) async {
    await tester.pumpWidget(const FlapamamakuApp());
    await tester.pumpAndSettle();

    expect(find.text('FLAPAMAMAKU'), findsOneWidget);
    expect(find.text('Anmelden'), findsWidgets);
    expect(find.text('Vereinsserver einrichten'), findsOneWidget);
  });
}
