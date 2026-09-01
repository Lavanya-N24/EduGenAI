import 'package:flutter/material.dart';
import '../main.dart' show AppColors, themeController;
import '../services/auth_service.dart';

class ThemeSelectorScreen extends StatefulWidget {
  const ThemeSelectorScreen({super.key});

  @override
  State<ThemeSelectorScreen> createState() => _ThemeSelectorScreenState();
}

class _ThemeSelectorScreenState extends State<ThemeSelectorScreen> {
  late ThemeMode _selectedMode;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _selectedMode = themeController.themeMode;
  }

  Future<void> _applyTheme(ThemeMode mode) async {
    setState(() => _selectedMode = mode);
    await themeController.setThemeMode(mode);
  }

  Future<void> _continueToHome() async {
    setState(() => _saving = true);

    final label = switch (_selectedMode) {
      ThemeMode.light => 'cream',
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
    };

    await AuthService.instance.updateThemeInDatabase(label);

    if (mounted) {
      Navigator.pushReplacementNamed(context, '/');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF161616) : AppColors.cream,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 16),
              Text(
                'Personalize Your Look',
                style: TextStyle(
                  fontSize: 28,
                  fontFamily: 'Georgia',
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : AppColors.ink,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Choose your preferred appearance for lessons and quizzes.',
                style: TextStyle(
                  fontSize: 14,
                  color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkFaint,
                  fontFamily: 'Roboto',
                ),
              ),
              const SizedBox(height: 32),

              _buildThemeOption(
                mode: ThemeMode.light,
                title: 'Warm Cream',
                subtitle: 'Parchment light palette, easy on the eyes',
                bgColor: const Color(0xFFFBF8EE),
                accentColor: const Color(0xFFD97706),
                isDarkActive: isDark,
              ),

              const SizedBox(height: 16),

              _buildThemeOption(
                mode: ThemeMode.dark,
                title: 'Obsidian Dark',
                subtitle: 'Deep contrast palette designed for night study',
                bgColor: const Color(0xFF161616),
                accentColor: const Color(0xFFF59E0B),
                isDarkActive: isDark,
              ),

              const SizedBox(height: 16),

              _buildThemeOption(
                mode: ThemeMode.system,
                title: 'Follow System',
                subtitle: 'Automatically syncs with your device settings',
                bgColor: Colors.grey.shade300,
                accentColor: Colors.grey.shade800,
                isDarkActive: isDark,
                isSplit: true,
              ),

              const Spacer(),

              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _saving ? null : _continueToHome,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: isDark ? const Color(0xFFF59E0B) : AppColors.accentTerracotta,
                    foregroundColor: isDark ? Colors.black87 : Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                  ),
                  child: _saving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text(
                          'Continue to Dashboard →',
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildThemeOption({
    required ThemeMode mode,
    required String title,
    required String subtitle,
    required Color bgColor,
    required Color accentColor,
    required bool isDarkActive,
    bool isSplit = false,
  }) {
    final isSelected = _selectedMode == mode;

    return GestureDetector(
      onTap: () => _applyTheme(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDarkActive ? const Color(0xFF222222) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected
                ? (isDarkActive ? const Color(0xFFF59E0B) : AppColors.accentTerracotta)
                : (isDarkActive ? const Color(0x1FFFFFFF) : AppColors.border),
            width: isSelected ? 2 : 1.2,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: (isDarkActive ? const Color(0xFFF59E0B) : AppColors.accentTerracotta)
                        .withValues(alpha: 0.15),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isDarkActive ? const Color(0x33FFFFFF) : AppColors.border,
                ),
                gradient: isSplit
                    ? const LinearGradient(
                        colors: [Color(0xFFFBF8EE), Color(0xFF161616)],
                        stops: [0.5, 0.5],
                      )
                    : null,
              ),
              child: Center(
                child: Container(
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    color: accentColor,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontFamily: 'Roboto',
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                      color: isDarkActive ? Colors.white : AppColors.ink,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 12,
                      color: isDarkActive ? const Color(0xFFA0A6C0) : AppColors.inkFaint,
                      fontFamily: 'Roboto',
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(
                Icons.check_circle_rounded,
                color: isDarkActive ? const Color(0xFFF59E0B) : AppColors.accentTerracotta,
              ),
          ],
        ),
      ),
    );
  }
}