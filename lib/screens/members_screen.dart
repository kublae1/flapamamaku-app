import 'package:flutter/material.dart';
import '../models/app_data.dart';
import 'content_detail_screens.dart';

class MembersScreen extends StatefulWidget {
  const MembersScreen({super.key});

  @override
  State<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends State<MembersScreen> {
  bool searching = false;
  String query = '';

  @override
  Widget build(BuildContext context) {
    final filtered = members.where((member) {
      final value = query.trim().toLowerCase();
      if (value.isEmpty) return true;
      return member.name.toLowerCase().contains(value) ||
          member.role.toLowerCase().contains(value);
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: searching
            ? TextField(
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Mitglied suchen',
                  border: InputBorder.none,
                ),
                onChanged: (value) => setState(() => query = value),
              )
            : const Text('Mitglieder'),
        actions: [
          IconButton(
            onPressed: () => setState(() {
              searching = !searching;
              if (!searching) query = '';
            }),
            icon: Icon(searching ? Icons.close : Icons.search),
          ),
        ],
      ),
      body: filtered.isEmpty
          ? const Center(child: Text('Keine Mitglieder gefunden'))
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: filtered.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final member = filtered[i];
                return ListTile(
                  leading: CircleAvatar(
                    child: Text(member.name.characters.first),
                  ),
                  title: Text(
                    member.name,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text('${member.role}\n${member.since}'),
                  isThreeLine: true,
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => MemberDetailScreen(member: member),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
