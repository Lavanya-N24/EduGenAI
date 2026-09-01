import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'firebase_options.dart';
import 'theme_controller.dart';
import 'screens/welcome.dart';
import 'screens/auth_screen.dart';
import 'screens/profile_setup.dart';
import 'screens/theme_selector.dart';
import 'screens/home.dart';
import 'screens/result.dart';
import 'screens/quiz.dart';
import 'screens/tutor.dart';
import 'screens/analytics.dart';
import 'screens/video_history.dart';

final themeController = ThemeController();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  // Load saved theme preference (Cream, Dark, or System)
  await themeController.loadSaved();
  
  runApp(const EduGenAIApp());
}

// ── Cream / Light Theme Palette ──────────────────────────────────────────────
class AppColors {
  static const cream            = Color(0xFFFBF8EE);
  static const creamBackground  = Color(0xFFFBF8EE);
  static const creamCard        = Color(0xFFFFFFFF);
  static const ink              = Color(0xFF261E14);
  static const inkDark          = Color(0xFF261E14);
  static const inkSoft          = Color(0xFF6B5E4D);
  static const inkMuted         = Color(0xFF6B5E4D);
  static const inkFaint         = Color(0xFFA89F91);
  static const accent           = Color(0xFF2D6A4F);
  static const accentSoft       = Color(0xFFD8EDDF);
  static const accentMid        = Color(0xFF52B788);
  static const accentTerracotta = Color(0xFFD97706);
  static const periwinkle       = Color(0xFF5C67F2);
  static const darkBackground   = Color(0xFF161616);
  static const border           = Color(0xFFE5DCC9);
  static const error            = Color(0xFFDC2626);
}

// ── Obsidian Dark Theme Palette ──────────────────────────────────────────────
class AppDarkColors {
  static const bg         = Color(0xFF161616);
  static const card       = Color(0xFF222222);
  static const ink        = Color(0xFFFFFFFF);
  static const inkFaint   = Color(0xFFA0A6C0);
  static const accent     = Color(0xFFF59E0B);
  static const accentSoft = Color(0x33F59E0B);
  static const border     = Color(0x1FFFFFFF);
}

class EduGenAIApp extends StatelessWidget {
  const EduGenAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: themeController,
      builder: (context, _) {
        // Auto-navigate to home if already logged in, otherwise show Welcome
        final initialRoute = FirebaseAuth.instance.currentUser != null
            ? '/'
            : '/welcome';

        return MaterialApp(
          title: 'EduGenAI',
          debugShowCheckedModeBanner: false,
          themeMode: themeController.themeMode,
          theme: _buildLightTheme(),
          darkTheme: _buildDarkTheme(),
          initialRoute: initialRoute,
          routes: {
            '/welcome': (context) => const WelcomeScreen(),
            '/auth': (context) => const AuthScreen(),
            '/profile-setup': (context) => const ProfileSetupScreen(),
            '/theme-selector': (context) => const ThemeSelectorScreen(),
            '/': (context) => const HomeScreen(),
            '/result': (context) => const ResultScreen(),
            '/quiz': (context) => const QuizScreen(),
            '/tutor': (context) => const TutorScreen(),
            '/analytics': (context) => const AnalyticsScreen(),
            '/history': (context) => const VideoHistoryScreen(),
          },
        );
      },
    );
  }

  ThemeData _buildLightTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorSchemeSeed: AppColors.accentTerracotta,
      scaffoldBackgroundColor: AppColors.cream,
      fontFamily: 'Georgia',
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.cream,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: AppColors.ink,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          fontFamily: 'Georgia',
        ),
        iconTheme: IconThemeData(color: AppColors.ink),
      ),
      cardTheme: CardThemeData(
        color: AppColors.creamCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.accentTerracotta,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            fontFamily: 'Roboto',
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.creamCard,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border, width: 1.2),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border, width: 1.2),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.accentTerracotta, width: 1.5),
        ),
        hintStyle: const TextStyle(color: AppColors.inkFaint, fontFamily: 'Roboto'),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
      textTheme: const TextTheme(
        bodyMedium: TextStyle(fontFamily: 'Roboto', color: AppColors.ink),
        bodySmall: TextStyle(fontFamily: 'Roboto', color: AppColors.inkSoft),
      ),
    );
  }

  ThemeData _buildDarkTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorSchemeSeed: AppDarkColors.accent,
      scaffoldBackgroundColor: AppDarkColors.bg,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: AppDarkColors.bg,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: AppDarkColors.ink,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
        iconTheme: IconThemeData(color: AppDarkColors.ink),
      ),
      cardTheme: CardThemeData(
        color: AppDarkColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: AppDarkColors.border),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppDarkColors.accent,
          foregroundColor: Colors.black87,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppDarkColors.card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppDarkColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppDarkColors.accent, width: 1.5),
        ),
        hintStyle: const TextStyle(color: AppDarkColors.inkFaint),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),
      textTheme: const TextTheme(
        bodyMedium: TextStyle(color: AppDarkColors.ink),
        bodySmall: TextStyle(color: AppDarkColors.inkFaint),
      ),
    );
  }
}