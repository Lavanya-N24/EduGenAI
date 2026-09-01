import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../main.dart' show AppColors, themeController;

class LoginSignupScreen extends StatefulWidget {
  final bool isSignUp;
  const LoginSignupScreen({super.key, this.isSignUp = false});

  @override
  State<LoginSignupScreen> createState() => _LoginSignupScreenState();
}

class _LoginSignupScreenState extends State<LoginSignupScreen> {
  late bool _isSignUp;
  final _formKey = GlobalKey<FormState>();

  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();

  bool _busy = false;
  bool _obscure = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _isSignUp = widget.isSignUp;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  void _onSuccess() {
    if (_isSignUp) {
      Navigator.of(context).pushReplacementNamed('/profile-setup');
    } else if (!themeController.hasChosen) {
      Navigator.of(context).pushReplacementNamed('/theme-selector');
    } else {
      Navigator.of(context).pushReplacementNamed('/');
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      if (_isSignUp) {
        await AuthService.instance.signUpWithEmail(
          _nameCtrl.text.trim(),
          _emailCtrl.text.trim(),
          _passCtrl.text,
        );
      } else {
        await AuthService.instance.signInWithEmail(
          _emailCtrl.text.trim(),
          _passCtrl.text,
        );
      }
      if (mounted) _onSuccess();
    } catch (e) {
      setState(() => _error = e.toString().replaceAll('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  children: [
                    Text(
                      _isSignUp ? 'Create Account' : 'Welcome Back',
                      style: TextStyle(
                        fontFamily: 'Georgia',
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: isDark ? Colors.white : AppColors.ink,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _isSignUp
                          ? 'Join EduGenAI to unlock custom AI study materials'
                          : 'Sign in with your email credentials',
                      style: const TextStyle(color: AppColors.inkSoft, fontSize: 14),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 28),

                    if (_isSignUp) ...[
                      TextFormField(
                        controller: _nameCtrl,
                        decoration: const InputDecoration(
                          hintText: 'Full Name',
                          prefixIcon: Icon(Icons.person_outline, color: AppColors.inkFaint),
                        ),
                        validator: (v) => v!.trim().isEmpty ? 'Please enter your name' : null,
                      ),
                      const SizedBox(height: 14),
                    ],

                    TextFormField(
                      controller: _emailCtrl,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        hintText: 'Email Address',
                        prefixIcon: Icon(Icons.email_outlined, color: AppColors.inkFaint),
                      ),
                      validator: (v) => !v!.contains('@') ? 'Enter a valid email' : null,
                    ),
                    const SizedBox(height: 14),

                    TextFormField(
                      controller: _passCtrl,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        hintText: 'Password',
                        prefixIcon: const Icon(Icons.lock_outline, color: AppColors.inkFaint),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility, color: AppColors.inkFaint),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) => v!.length < 6 ? 'Password must be at least 6 characters' : null,
                    ),

                    const SizedBox(height: 24),

                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: _busy ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.accentTerracotta,
                          foregroundColor: Colors.white,
                        ),
                        child: _busy
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                              )
                            : Text(
                                _isSignUp ? 'Create Account' : 'Sign In',
                                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                              ),
                      ),
                    ),

                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13), textAlign: TextAlign.center),
                    ],

                    const SizedBox(height: 18),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _isSignUp ? 'Already have an account?' : "Don't have an account?",
                          style: const TextStyle(color: AppColors.inkSoft, fontSize: 13),
                        ),
                        TextButton(
                          onPressed: () => setState(() => _isSignUp = !_isSignUp),
                          child: Text(
                            _isSignUp ? 'Sign In' : 'Sign Up',
                            style: const TextStyle(color: AppColors.accentTerracotta, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}