import 'package:flutter/material.dart';
import 'data/app_store.dart';
import 'screens/home_shell.dart';

void main() {
  runApp(const FlapamamakuApp());
}

class FlapamamakuApp extends StatefulWidget {
  const FlapamamakuApp({super.key});

  @override
  State<FlapamamakuApp> createState() => _FlapamamakuAppState();
}

class _FlapamamakuAppState extends State<FlapamamakuApp> {
  final AppStore store = AppStore();

  @override
  Widget build(BuildContext context) {
    const burgundy = Color(0xFF8A101B);

    return AppStoreScope(
      store: store,
      child: MaterialApp(
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
      ),
    );
  }
}
