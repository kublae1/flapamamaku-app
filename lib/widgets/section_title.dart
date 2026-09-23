import 'package:flutter/material.dart';

class SectionTitle extends StatelessWidget {
  final String title;
  final String? action;
  const SectionTitle(this.title, {this.action, super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
        if (action != null) Text(action!, style: TextStyle(color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
