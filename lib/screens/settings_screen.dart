import 'package:flutter/material.dart';

import '../data/app_store.dart';

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
      appBar: AppBar(title: const Text('Einstellungen')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Farbwahl',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Wähle die Hauptfarbe der App. Die Auswahl gilt nur auf diesem Gerät.',
          ),
          const SizedBox(height: 14),
          ...colors.map((entry) {
            final (name, value) = entry;
            final selected = store.themeColorValue == value;
            return Card(
              child: ListTile(
                onTap: () => store.setThemeColor(value),
                leading: CircleAvatar(
                  backgroundColor: Color(value),
                  child: selected
                      ? const Icon(Icons.check, color: Colors.white)
                      : null,
                ),
                title: Text(name),
                trailing: selected
                    ? const Icon(Icons.radio_button_checked)
                    : const Icon(Icons.radio_button_off),
              ),
            );
          }),
        ],
      ),
    );
  }
}
