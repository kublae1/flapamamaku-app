import 'package:flutter/material.dart';

class FlapBrand {
  static const burgundy = Color(0xFF8A101B);
  static const burgundyDark = Color(0xFF2D0A0E);
  static const charcoal = Color(0xFF111315);
  static const warmBackground = Color(0xFFF4EFE9);
  static const gold = Color(0xFFC7A35A);

  static ThemeData theme(Color appColor) {
    final scheme = ColorScheme.fromSeed(
      seedColor: appColor,
      brightness: Brightness.light,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(
        primary: appColor,
        secondary: gold,
        surface: Colors.white,
      ),
      scaffoldBackgroundColor: warmBackground,
      appBarTheme: const AppBarTheme(
        backgroundColor: charcoal,
        foregroundColor: Colors.white,
        centerTitle: false,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: const BorderSide(color: Color(0x14000000)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: charcoal,
        indicatorColor: burgundy,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            color: states.contains(WidgetState.selected)
                ? Colors.white
                : Colors.white70,
            fontWeight: FontWeight.w700,
            fontSize: 12,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? Colors.white
                : Colors.white70,
          ),
        ),
      ),
    );
  }
}
