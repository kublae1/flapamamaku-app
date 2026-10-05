import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'data/app_store.dart';
import 'data/runtime_content_policy.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'screens/biometric_lock_screen.dart';
import 'theme/flap_brand.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Managed white-label builds are permanently bound to the server compiled
  // into the APK. Older test builds could leave a manually selected pilot
  // server in SharedPreferences; remove that stale override before AppStore is
  // constructed so FLAPAMAMAKU can never reopen another club's server.
  const allowServerChange = bool.fromEnvironment(
    'ALLOW_SERVER_CHANGE',
    defaultValue: true,
  );
  if (!allowServerChange) {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('flapamamaku_server_url');
  }

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
        // Phase-1 invariant: a configured club server is the source of truth.
        // Bundled development fixtures must never be presented as live data.
        store.enforceServerContentPolicy();

        return AppStoreScope(
          store: store,
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            title: store.appName,
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
                if (!store.serverConfigured || !store.isAuthenticated) {
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
