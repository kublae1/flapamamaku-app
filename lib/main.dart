import 'package:flutter/material.dart';
import 'data/app_store.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'screens/password_change_screen.dart';
import 'screens/biometric_lock_screen.dart';
import 'screens/club_selection_screen.dart';
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
  bool _minimumSplashElapsed = false;

  @override
  void initState() {
    super.initState();
    Future<void>.delayed(const Duration(milliseconds: 2500), () {
      if (!mounted) return;
      setState(() => _minimumSplashElapsed = true);
    });
  }

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
        return AppStoreScope(
          store: store,
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            title: store.appName,
            theme: FlapBrand.theme(store.themeColor),
            home: Builder(
              builder: (context) {
                final store = AppStoreScope.of(context);
                if (!_minimumSplashElapsed || !store.authReady) {
                  return Scaffold(
                    backgroundColor: FlapBrand.charcoal,
                    body: SafeArea(
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 168,
                              height: 168,
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(38),
                                boxShadow: const [
                                  BoxShadow(
                                    color: Color(0x33000000),
                                    blurRadius: 24,
                                    offset: Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: Image.asset(
                                'assets/FLAPAMAMAKU App-Icon.png',
                                fit: BoxFit.contain,
                              ),
                            ),
                            const SizedBox(height: 22),
                            Text(
                              store.appName,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: store.themeColor,
                                fontSize: 24,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }
                if (store.serverConfigured && store.biometricUnlockPending) {
                  return const BiometricLockScreen();
                }
                if (!store.serverConfigured || !store.isAuthenticated) {
                  return const LoginScreen();
                }
                if (store.mustChangePassword) {
                  return const PasswordChangeScreen(forced: true);
                }
                if (store.clubSelectionRequired) {
                  return const ClubSelectionScreen();
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
