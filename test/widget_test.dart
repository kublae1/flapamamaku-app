import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/main.dart';

void main() {
  testWidgets('FLAPAMAMAKU mockup navigation is available', (tester) async {
    await tester.pumpWidget(const FlapamamakuApp());

    expect(find.text('FLAPAMAMAKU'), findsOneWidget);
    expect(find.text('Jahresmotto'), findsOneWidget);
    expect(find.text('Start'), findsOneWidget);
    expect(find.text('News'), findsOneWidget);
    expect(find.text('Termine'), findsOneWidget);
    expect(find.text('Galerie'), findsOneWidget);
    expect(find.text('Mehr'), findsOneWidget);
  });
}
