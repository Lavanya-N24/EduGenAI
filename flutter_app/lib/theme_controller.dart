import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Manages application theme selection, notifying listeners on changes,
/// and persisting choices both locally and for Firestore synchronization.
class ThemeController extends ChangeNotifier {
  static const String _modeKey = 'theme_mode';
  static const String _chosenKey = 'theme_chosen';

  // Default to Light (Cream) theme for initial warm aesthetic
  ThemeMode _themeMode = ThemeMode.light;
  bool _hasChosen = false;

  ThemeMode get themeMode => _themeMode;
  bool get hasChosen => _hasChosen;

  /// Loads saved theme settings from local device storage before runApp.
  Future<void> loadSaved() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_modeKey);

      if (saved != null) {
        _themeMode = switch (saved) {
          'light' || 'cream' => ThemeMode.light,
          'dark' => ThemeMode.dark,
          _ => ThemeMode.system,
        };
      } else {
        _themeMode = ThemeMode.light;
      }

      _hasChosen = prefs.getBool(_chosenKey) ?? false;
    } catch (e) {
      // Fallback defaults if storage read fails
      _themeMode = ThemeMode.light;
      _hasChosen = false;
    }
    notifyListeners();
  }

  /// Sets the theme mode and persists it locally.
  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    _hasChosen = true;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      final value = switch (mode) {
        ThemeMode.light => 'light',
        ThemeMode.dark => 'dark',
        ThemeMode.system => 'system',
      };
      await prefs.setString(_modeKey, value);
      await prefs.setBool(_chosenKey, true);
    } catch (_) {
      // Ignore write errors during dev/testing
    }
  }

  /// Alias for `setThemeMode` to maintain compatibility with screens calling `setMode`
  Future<void> setMode(ThemeMode mode) => setThemeMode(mode);

  /// Helper getter to convert current mode into a string label for Firestore
  String get themeLabel {
    return switch (_themeMode) {
      ThemeMode.light => 'cream',
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
    };
  }
}