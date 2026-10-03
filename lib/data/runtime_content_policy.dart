import 'app_store.dart';

/// Pure Phase-1 rule used by tests and by the runtime guard.
bool allowBundledDemoContent({required bool serverConfigured}) =>
    !serverConfigured;

/// Enforces the Phase-1 rule that productive, server-configured club apps must
/// never expose bundled demo content as if it were server data.
extension RuntimeContentPolicy on AppStore {
  void enforceServerContentPolicy() {
    if (allowBundledDemoContent(serverConfigured: api.isConfigured) ||
        isUsingServer) {
      return;
    }

    // Before login and after logout the UI must be empty rather than showing
    // development fixtures. A successful sync or offline-cache restore
    // repopulates these collections with real club data afterwards.
    if (!isAuthenticated) {
      news.clear();
      events.clear();
      members.clear();
      memberFilters.clear();
      content.clear();
    }
  }
}
