import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:flapamamaku_app/data/api_service.dart';
import 'package:flapamamaku_app/data/app_store.dart';
import 'package:flapamamaku_app/models/app_data.dart';
import 'package:flapamamaku_app/screens/home_shell.dart';
import 'package:flapamamaku_app/theme/flap_brand.dart';

Widget _appWithStore(AppStore store) {
  return AppStoreScope(
    store: store,
    child: MaterialApp(
      theme: FlapBrand.theme(store.themeColor),
      home: const HomeShell(),
    ),
  );
}

AppStore _authenticatedStore() {
  final store = AppStore(api: ApiService(baseUrl: 'https://verein.example.test'));
  store.authReady = true;
  store.isAuthenticated = true;
  store.currentUser = {
    'username': 'tester',
    'member_name': 'Test Mitglied',
    'can_news': true,
    'can_events': true,
    'can_members': true,
    'can_documents': true,
    'can_photos': true,
    'can_gallery_upload': true,
    'can_polls': true,
    'can_links': true,
    'can_contact': true,
    'can_about': true,
    'can_admin_page': true,
    'can_manage_users': false,
  };
  store.news
    ..clear()
    ..add(
      const NewsItem(
        '28.09.2026',
        'E2E News',
        'Dieser Eintrag prüft den kompletten Navigationsfluss.',
        id: 501,
        createdAt: '2026-09-28T12:00:00',
      ),
    );
  store.events
    ..clear()
    ..add(
      const EventItem(
        '28',
        'SEP',
        'E2E Termin',
        'Luzern',
        '20:00 Uhr',
        id: 601,
        eventDate: '2026-09-28',
        registrationCount: 3,
      ),
    );
  store.content
    ..clear()
    ..addAll([
      const ContentItem(
        id: 701,
        section: 'gallery',
        title: 'E2E Galerie',
        text: 'Galerietest',
        createdAt: '2026-09-28T12:00:00',
      ),
      const ContentItem(
        id: 702,
        section: 'polls',
        title: 'E2E Umfrage',
        text: 'Abstimmungstest',
        pollOptions: ['Ja', 'Nein'],
        createdAt: '2026-09-28T12:00:00',
      ),
    ]);
  return store;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('authenticated member can navigate core app areas end to end',
      (tester) async {
    final store = _authenticatedStore();
    addTearDown(store.dispose);

    await tester.pumpWidget(_appWithStore(store));
    await tester.pump();

    expect(find.text('E2E News'), findsOneWidget);
    expect(find.text('Start'), findsOneWidget);
    expect(find.text('News'), findsWidgets);
    expect(find.text('Termine'), findsOneWidget);
    expect(find.text('Galerie'), findsOneWidget);
    expect(find.text('Mehr'), findsOneWidget);

    await tester.tap(find.text('News').last);
    await tester.pumpAndSettle();
    expect(find.text('E2E News'), findsOneWidget);

    await tester.tap(find.text('Termine'));
    await tester.pumpAndSettle();
    expect(find.text('E2E Termin'), findsOneWidget);
    expect(find.text('3 angemeldet'), findsOneWidget);

    await tester.tap(find.text('Galerie'));
    await tester.pumpAndSettle();
    expect(find.text('E2E Galerie'), findsOneWidget);

    await tester.tap(find.text('Mehr'));
    await tester.pumpAndSettle();
    expect(find.text('Mitglieder'), findsOneWidget);
    expect(find.text('Einstellungen'), findsOneWidget);
    expect(find.text('Administration'), findsOneWidget);
    expect(find.text('E2E Umfrage'), findsNothing);

    await tester.tap(find.text(store.labelPolls));
    await tester.pumpAndSettle();
    expect(find.text('E2E Umfrage'), findsOneWidget);
  });

  testWidgets('module visibility and permissions survive the full menu flow',
      (tester) async {
    final store = _authenticatedStore();
    addTearDown(store.dispose);
    store.showSujet = false;
    store.showArchive = false;
    store.showPhotos = false;
    store.showDocuments = false;
    store.showPolls = true;
    store.labelPolls = 'Vereinsabstimmungen';
    store.showLinks = false;
    store.currentUser = {
      ...?store.currentUser,
      'can_news': false,
      'can_events': false,
      'can_members': false,
      'can_documents': false,
      'can_photos': false,
      'can_gallery_upload': false,
      'can_polls': false,
      'can_links': false,
      'can_contact': false,
      'can_about': false,
      'can_admin_page': false,
      'can_manage_users': false,
    };

    await tester.pumpWidget(_appWithStore(store));
    await tester.pump();

    await tester.tap(find.text('Mehr'));
    await tester.pumpAndSettle();

    expect(find.text('Vereinsabstimmungen'), findsOneWidget);
    expect(find.text('Sujet nächstes Jahr'), findsNothing);
    expect(find.text('Vergangene Sujet'), findsNothing);
    expect(find.text('Fotoalben'), findsNothing);
    expect(find.text('Dokumente'), findsNothing);
    expect(find.text('Links'), findsNothing);
    expect(find.text('Administration'), findsNothing);
  });

  test('friendly errors never expose raw HTTP bodies', () {
    const serverError = ApiException(
      'Der Server hat momentan ein Problem. Bitte später nochmals versuchen.',
      statusCode: 500,
    );
    expect(
      friendlyErrorMessage(serverError),
      'Der Server hat momentan ein Problem. Bitte später nochmals versuchen.',
    );

    expect(
      friendlyErrorMessage(
        Exception('SocketException: Failed host lookup'),
      ),
      'Keine Verbindung zum Server. Bitte Internetverbindung prüfen.',
    );
  });
}
