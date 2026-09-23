import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/main.dart';

void main() {
  testWidgets('FLAPAMAMAKU app starts with version 0.2 navigation', (tester) async {
    await tester.pumpWidget(const FlapamamakuApp());

    expect(find.text('FLAPAMAMAKU'), findsOneWidget);
    expect(find.text('Jahresmotto'), findsOneWidget);
    expect(find.text('News'), findsOneWidget);
    expect(find.text('Termine'), findsOneWidget);
    expect(find.text('Mitglieder'), findsOneWidget);
  });
}
