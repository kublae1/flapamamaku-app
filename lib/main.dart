import 'package:flutter/material.dart';
import 'data/app_store.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'screens/biometric_lock_screen.dart';
import 'theme/flap_brand.dart';

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
  void dispose() {
    store.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final appColor = store.themeColor;
        return AppStoreScope(
          store: store,
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'FLAPAMAMAKU',
            theme: FlapBrand.theme(store.themeColor),
            home: Builder(
              builder: (context) {
                final store = AppStoreScope.of(context);
                if (!store.authReady) {
                  return const Scaffold(
                    body: Center(child: CircularProgressIndicator()),
                  );
                }
                if (store.serverConfigured && store.biometricUnlockPending) {
                  return const BiometricLockScreen();
                }
                if (store.serverConfigured && !store.isAuthenticated) {
                  return const LoginScreen();
                }
                return const HomeShell();
              },
            ),
          ),
        );
      },
    );
  }
}
