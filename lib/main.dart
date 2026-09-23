import 'package:flutter/material.dart';
import 'screens/home_shell.dart';

void main() {
  runApp(const FlapamamakuApp());
}

class FlapamamakuApp extends StatelessWidget {
  const FlapamamakuApp({super.key});

  @override
  Widget build(BuildContext context) {
    const burgundy = Color(0xFF8A101B);
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'FLAPAMAMAKU',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: burgundy),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF7F5F2),
        appBarTheme: const AppBarTheme(
          backgroundColor: burgundy,
          foregroundColor: Colors.white,
          centerTitle: true,
        ),
      ),
      home: const HomeShell(),
    );
  }
}
