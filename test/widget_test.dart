import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/main.dart';

void main() {
  testWidgets('login and server setup are available without a configured server',
      (tester) async {
    await tester.pumpWidget(const FlapamamakuApp());

    for (var i = 0; i < 20 && find.text('Vereinsserver einrichten').evaluate().isEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    expect(find.text('FLAPAMAMAKU'), findsOneWidget);
    expect(find.text('Anmelden'), findsWidgets);
    expect(find.text('Vereinsserver einrichten'), findsOneWidget);
  });
}
