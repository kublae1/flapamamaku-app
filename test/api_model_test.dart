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
      'phone_mobile': '+41 79 000 00 00',
      'phone_private': '041 000 00 00',
      'phone_work': '041 111 11 11',
      'occupation': 'Metzger',
      'employer': 'Beispiel AG',
      'email': 'max@example.test',
      'address': 'Luzern',
    });

    expect(member.partnerName, 'Anna Muster');
    expect(member.phoneMobile, '+41 79 000 00 00');
    expect(member.phonePrivate, '041 000 00 00');
    expect(member.phoneWork, '041 111 11 11');
    expect(member.occupation, 'Metzger');
    expect(member.employer, 'Beispiel AG');
    expect(member.address, 'Luzern');
  });
  test('maps unified content media payload', () {
    final item = ContentItem.fromJson({
      'id': 7,
      'section': 'photos',
      'title': 'Ausflug',
      'created_at': '2026-09-28T10:00:00+00:00',
      'images': [
        {
          'id': 21,
          'url': 'https://example.test/media/21',
          'sort_order': 2,
          'created_at': '2026-09-28T10:01:00+00:00',
          'legacy': false,
        },
        {
          'id': 20,
          'url': 'https://example.test/media/20',
          'sort_order': 1,
          'created_at': '2026-09-28T10:00:30+00:00',
          'legacy': false,
        },
      ],
      'image_urls': [
        'https://example.test/media/21',
        'https://example.test/media/20',
      ],
    });

    expect(item.mediaImages.length, 2);
    expect(item.mediaImages.first.id, 21);
    expect(item.mediaImages.first.url, 'https://example.test/media/21');
    expect(item.imageIds, [21, 20]);
    expect(item.imageSortOrders, [2, 1]);
    expect(item.imageUrls, [
      'https://example.test/media/21',
      'https://example.test/media/20',
    ]);
  });

}
