import 'package:flutter/material.dart';

import '../data/app_store.dart';
import '../theme/flap_brand.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const colors = <(String, int)>[
    ('Burgund', 0xFF8A101B),
    ('Dunkelrot', 0xFFB3261E),
    ('Blau', 0xFF2457A7),
    ('Grün', 0xFF2E6B3A),
    ('Violett', 0xFF6D3A8C),
    ('Dunkelorange', 0xFF9A4F00),
  ];

  @override
  Widget build(BuildContext context) {
    final store = AppStoreScope.of(context);

    return Scaffold(
      backgroundColor: FlapBrand.charcoal,
      appBar: AppBar(
        title: const Text(
          'Einstellungen',
          style: TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
        children: [
          const Text(
            'APP-DESIGN',
            style: TextStyle(
              color: FlapBrand.gold,
              fontWeight: FontWeight.w900,
              fontSize: 11,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Farbwahl',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 23,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Wähle die Hauptfarbe der App. Die Auswahl gilt nur auf diesem Gerät.',
            style: TextStyle(color: Colors.white60, height: 1.35),
          ),
          const SizedBox(height: 16),
          ...colors.map((entry) {
            final (name, value) = entry;
            final selected = store.themeColorValue == value;
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Material(
                color: const Color(0xFF191B1E),
                borderRadius: BorderRadius.circular(18),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => store.setThemeColor(value),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 13,
                    ),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 22,
                          backgroundColor: Color(value),
                          child: selected
                              ? const Icon(Icons.check_rounded, color: Colors.white)
                              : null,
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        Icon(
                          selected
                              ? Icons.radio_button_checked_rounded
                              : Icons.radio_button_off_rounded,
                          color: selected ? FlapBrand.gold : Colors.white38,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
