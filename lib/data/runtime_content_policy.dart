import 'app_store.dart';

/// Enforces the Phase-1 rule that productive, server-configured club apps must
/// never expose bundled demo content as if it were server data.
extension RuntimeContentPolicy on AppStore {
  void enforceServerContentPolicy() {
    if (!api.isConfigured || isUsingServer) return;

    // Before login and after logout the UI must be empty rather than showing
    // the FLAPAMAMAKU development fixtures. A successful sync or offline-cache
    // restore repopulates these collections with real data afterwards.
    if (!isAuthenticated) {
      news.clear();
      events.clear();
      members.clear();
      memberFilters.clear();
      content.clear();
    }
  }
}
