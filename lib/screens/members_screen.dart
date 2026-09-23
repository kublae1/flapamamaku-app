import 'package:flutter/material.dart';
import '../models/app_data.dart';

class MembersScreen extends StatelessWidget {
  const MembersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mitglieder'), actions: [IconButton(onPressed: () {}, icon: const Icon(Icons.search))]),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: members.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (_, i) {
          final m = members[i];
          return ListTile(
            leading: CircleAvatar(child: Text(m.name.characters.first)),
            title: Text(m.name, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('${m.role}\n${m.since}'),
            isThreeLine: true,
            trailing: Wrap(spacing: 2, children: [
              IconButton(onPressed: () {}, icon: const Icon(Icons.phone_outlined)),
              IconButton(onPressed: () {}, icon: const Icon(Icons.mail_outline)),
            ]),
          );
        },
      ),
    );
  }
}
