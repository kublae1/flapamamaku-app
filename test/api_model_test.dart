import 'package:flutter_test/flutter_test.dart';
import 'package:flapamamaku_app/models/app_data.dart';

void main() {
  test('maps backend news payload', () {
    final item = NewsItem.fromJson({
      'id': 5,
      'date': '23.09.2026',
      'title': 'Neue News',
      'text': 'Test',
      'created_at': '2026-09-23T20:00:00+00:00',
      'image_url': 'https://example.test/photo.jpg',
    });

    expect(item.id, 5);
    expect(item.title, 'Neue News');
    expect(item.imageUrl, 'https://example.test/photo.jpg');
  });

  test('maps backend member payload including partner', () {
    final member = MemberItem.fromJson({
      'id': 2,
      'name': 'Max Muster',
      'role': 'Präsident',
      'since': 'seit 2020',
      'partner_name': 'Anna Muster',
      'phone': '+41 79 000 00 00',
      'email': 'max@example.test',
      'address': 'Luzern',
    });

    expect(member.partnerName, 'Anna Muster');
    expect(member.phone, '+41 79 000 00 00');
    expect(member.address, 'Luzern');
  });
}
