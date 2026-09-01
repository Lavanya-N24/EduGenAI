import 'package:flutter/material.dart';
import '../main.dart' show AppColors;
import '../services/auth_service.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  bool _isLoading = false;

  Future<void> _handleGoogleSignIn() async {
    setState(() => _isLoading = true);
    try {
      final user = await AuthService.instance.signInWithGoogle();
      if (user != null && mounted) {
        if (user.isNewUser) {
          Navigator.pushReplacementNamed(context, '/profile-setup');
        } else {
          Navigator.pushReplacementNamed(context, '/');
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Google Sign-In failed: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : AppColors.cream;
    final cardBg = isDark ? const Color(0xFF222222) : Colors.white;

    return Scaffold(
      backgroundColor: bgColor,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Top Mascot / Badge
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF3EFE6),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.auto_awesome_rounded,
                    size: 36,
                    color: Color(0xFFD97706),
                  ),
                ),
                const SizedBox(height: 24),

                // Main Title & Subtext
                Text(
                  'Welcome to EduGenAI',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: isDark ? Colors.white : AppColors.ink,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Create, learn, and master any subject with personalized AI lessons and quizzes.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Roboto',
                    fontSize: 14,
                    height: 1.4,
                    color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                  ),
                ),
                const SizedBox(height: 36),

                // 1. Get Started - Sign Up
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: () => Navigator.pushNamed(context, '/auth', arguments: {'isSignUp': true}),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFD97706),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
                      elevation: 0,
                    ),
                    child: const Text(
                      'Get Started — Sign Up',
                      style: TextStyle(fontFamily: 'Roboto', fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // 2. Already have an account? Sign In
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: OutlinedButton(
                    onPressed: () => Navigator.pushNamed(context, '/auth', arguments: {'isSignUp': false}),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF2D6A4F),
                      side: const BorderSide(color: Color(0xFF2D6A4F), width: 1.5),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
                    ),
                    child: const Text(
                      'Already have an account? Sign In',
                      style: TextStyle(fontFamily: 'Roboto', fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // 3. Continue with Google Button
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: OutlinedButton(
                    onPressed: _isLoading ? null : _handleGoogleSignIn,
                    style: OutlinedButton.styleFrom(
                      backgroundColor: cardBg,
                      foregroundColor: isDark ? Colors.white : AppColors.ink,
                      side: BorderSide(color: isDark ? Colors.white12 : AppColors.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFD97706)),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: const [
                              _GoogleLogo(size: 20),
                              SizedBox(width: 12),
                              Text(
                                'Continue with Google',
                                style: TextStyle(
                                  fontFamily: 'Roboto',
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 24),

                // 4. Explore as Guest
                GestureDetector(
                  onTap: () => Navigator.pushReplacementNamed(context, '/'),
                  child: const Text(
                    'Explore as Guest',
                    style: TextStyle(
                      fontFamily: 'Roboto',
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF2D6A4F),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Google 4-Color Vector Logo Widget ─────────────────────────────────────────
class _GoogleLogo extends StatelessWidget {
  final double size;
  const _GoogleLogo({this.size = 20});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        'G',
        style: TextStyle(
          fontFamily: 'Roboto',
          fontSize: size * 0.85,
          fontWeight: FontWeight.w900,
          color: const Color(0xFF4285F4),
        ),
      ),
    );
  }
}