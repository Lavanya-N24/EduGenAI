import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../main.dart' show AppColors, themeController;
import '../services/auth_service.dart';

class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen>
    with SingleTickerProviderStateMixin {
  final _nameController = TextEditingController();
  final _ageController = TextEditingController();
  final _customGoalController = TextEditingController();
  final _oldPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  String _selectedRole = 'Student';
  String _selectedGoal = 'Exam preparation & concept mastery';

  bool _isSaving = false;
  bool _isLoading = true;
  bool _showOldPassword = false;
  bool _showNewPassword = false;
  bool _showConfirmPassword = false;

  late AnimationController _animController;
  late Animation<double> _fadeAnim;

  final List<String> _roles = [
    'Student',
    'Self-Learner',
    'Developer / Engineer',
    'Educator / Teacher',
    'Professional',
  ];

  final List<String> _goals = [
    'Exam preparation & concept mastery',
    'Visual video summaries of long topics',
    'Interactive testing & smart quizzes',
    'Quick AI tutoring & revision',
    'Other / Custom goal',
  ];

  // Determine if the user signed in with email/password
  bool get _isEmailUser {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return false;
    return user.providerData.any((p) => p.providerId == 'password');
  }

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 480),
    );
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeOut);
    _loadProfile();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _customGoalController.dispose();
    _oldPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    _animController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    setState(() => _isLoading = true);
    try {
      final data = await AuthService.instance.getUserProfileData();
      if (data != null && mounted) {
        setState(() {
          _nameController.text = data['displayName'] ?? '';
          _ageController.text = data['age'] != null && data['age'] != 'Not specified'
              ? data['age'].toString()
              : '';
          final role = data['role'] as String?;
          if (role != null && _roles.contains(role)) {
            _selectedRole = role;
          }
          final goal = data['learningGoal'] as String?;
          if (goal != null) {
            if (_goals.contains(goal)) {
              _selectedGoal = goal;
            } else {
              _selectedGoal = 'Other / Custom goal';
              _customGoalController.text = goal;
            }
          }
        });
      }
    } catch (e) {
      debugPrint('Error loading profile: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
        _animController.forward();
      }
    }
  }

  Future<void> _handleSave() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      _showSnack('Please enter your name', isError: true);
      return;
    }

    setState(() => _isSaving = true);
    try {
      final finalGoal = _selectedGoal == 'Other / Custom goal'
          ? (_customGoalController.text.trim().isNotEmpty
              ? _customGoalController.text.trim()
              : 'General Learning')
          : _selectedGoal;

      await AuthService.instance.saveUserProfileDetails(
        name: name,
        age: _ageController.text.trim().isNotEmpty
            ? _ageController.text.trim()
            : 'Not specified',
        role: _selectedRole,
        goal: finalGoal,
      );

      if (mounted) {
        _showSnack('Profile saved successfully ✓');
      }
    } catch (e) {
      if (mounted) {
        _showSnack('Error saving profile: $e', isError: true);
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _handleChangePassword() async {
    final oldPw = _oldPasswordController.text.trim();
    final newPw = _newPasswordController.text.trim();
    final confirmPw = _confirmPasswordController.text.trim();

    if (oldPw.isEmpty || newPw.isEmpty || confirmPw.isEmpty) {
      _showSnack('Please fill in all password fields', isError: true);
      return;
    }
    if (newPw != confirmPw) {
      _showSnack('New passwords do not match', isError: true);
      return;
    }
    if (newPw.length < 6) {
      _showSnack('Password must be at least 6 characters', isError: true);
      return;
    }

    setState(() => _isSaving = true);
    try {
      await AuthService.instance.updatePassword(
        oldPassword: oldPw,
        newPassword: newPw,
      );
      if (mounted) {
        _oldPasswordController.clear();
        _newPasswordController.clear();
        _confirmPasswordController.clear();
        Navigator.pop(context); // close dialog if open
        _showSnack('Password updated successfully ✓');
      }
    } catch (e) {
      if (mounted) {
        _showSnack('Error: $e', isError: true);
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  void _showSnack(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? AppColors.error : const Color(0xFF2D6A4F),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  void _showChangePasswordDialog(bool isDark) {
    _oldPasswordController.clear();
    _newPasswordController.clear();
    _confirmPasswordController.clear();
    _showOldPassword = false;
    _showNewPassword = false;
    _showConfirmPassword = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          final cardBg = isDark ? const Color(0xFF222222) : Colors.white;
          final textColor = isDark ? Colors.white : AppColors.ink;
          return AlertDialog(
            backgroundColor: cardBg,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Text(
              'Change Password',
              style: TextStyle(
                fontFamily: 'Georgia',
                fontWeight: FontWeight.bold,
                color: textColor,
              ),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _pwField(
                  controller: _oldPasswordController,
                  label: 'Current Password',
                  obscure: !_showOldPassword,
                  onToggle: () =>
                      setDialogState(() => _showOldPassword = !_showOldPassword),
                  isDark: isDark,
                ),
                const SizedBox(height: 12),
                _pwField(
                  controller: _newPasswordController,
                  label: 'New Password',
                  obscure: !_showNewPassword,
                  onToggle: () =>
                      setDialogState(() => _showNewPassword = !_showNewPassword),
                  isDark: isDark,
                ),
                const SizedBox(height: 12),
                _pwField(
                  controller: _confirmPasswordController,
                  label: 'Confirm New Password',
                  obscure: !_showConfirmPassword,
                  onToggle: () => setDialogState(
                      () => _showConfirmPassword = !_showConfirmPassword),
                  isDark: isDark,
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text('Cancel',
                    style: TextStyle(color: isDark ? Colors.white54 : AppColors.inkSoft)),
              ),
              ElevatedButton(
                onPressed: _isSaving ? null : _handleChangePassword,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFD97706),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14)),
                ),
                child: _isSaving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Update'),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _pwField({
    required TextEditingController controller,
    required String label,
    required bool obscure,
    required VoidCallback onToggle,
    required bool isDark,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      style: TextStyle(color: isDark ? Colors.white : AppColors.ink),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(
            fontSize: 13,
            color: isDark ? Colors.white54 : AppColors.inkSoft),
        filled: true,
        fillColor: isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF5F3EC),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        suffixIcon: IconButton(
          icon: Icon(
            obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
            size: 18,
            color: isDark ? Colors.white38 : AppColors.inkFaint,
          ),
          onPressed: onToggle,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF141414) : const Color(0xFFFAF9F5);
    final cardBg = isDark ? const Color(0xFF1E1E1E) : Colors.white;
    final textColor = isDark ? Colors.white : AppColors.ink;
    final subColor = isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft;
    final borderColor = isDark ? const Color(0xFF2E2E2C) : AppColors.border;
    final sectionHeaderColor =
        isDark ? const Color(0xFF888888) : AppColors.inkFaint;

    final user = AuthService.instance.currentUser;
    final displayName = _nameController.text.isNotEmpty
        ? _nameController.text
        : (user?.name ?? 'Learner');
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'L';
    final email = user?.email ?? '';

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: bgColor,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded,
              size: 20, color: textColor),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Profile Settings',
          style: TextStyle(
            fontFamily: 'Georgia',
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: textColor,
          ),
        ),
        centerTitle: true,
        actions: [
          TextButton(
            onPressed: _isSaving ? null : _handleSave,
            child: _isSaving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Color(0xFFD97706)),
                  )
                : const Text(
                    'Save',
                    style: TextStyle(
                      color: Color(0xFFD97706),
                      fontWeight: FontWeight.w700,
                      fontFamily: 'Roboto',
                      fontSize: 15,
                    ),
                  ),
          ),
        ],
      ),
      body: _isLoading
          ? Center(
              child: CircularProgressIndicator(
                color: const Color(0xFFD97706),
                strokeWidth: 2.5,
              ),
            )
          : FadeTransition(
              opacity: _fadeAnim,
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 560),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Avatar Header ──────────────────────────────────
                        Center(
                          child: Column(
                            children: [
                              Hero(
                                tag: 'profile_avatar',
                                child: Container(
                                  width: 88,
                                  height: 88,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: const LinearGradient(
                                      colors: [
                                        Color(0xFFD97706),
                                        Color(0xFFF59E0B)
                                      ],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFFD97706)
                                            .withValues(alpha: 0.3),
                                        blurRadius: 18,
                                        offset: const Offset(0, 6),
                                      ),
                                    ],
                                  ),
                                  child: Center(
                                    child: Text(
                                      initial,
                                      style: const TextStyle(
                                        fontSize: 36,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                        fontFamily: 'Georgia',
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                displayName,
                                style: TextStyle(
                                  fontFamily: 'Georgia',
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                  color: textColor,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                email,
                                style: TextStyle(
                                  fontFamily: 'Roboto',
                                  fontSize: 13,
                                  color: subColor,
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 28),

                        // ── Profile Section ────────────────────────────────
                        _sectionHeader('PROFILE INFORMATION', sectionHeaderColor),
                        const SizedBox(height: 10),
                        _settingsCard(
                          isDark: isDark,
                          cardBg: cardBg,
                          borderColor: borderColor,
                          child: Column(
                            children: [
                              _fieldTile(
                                label: 'Full Name',
                                icon: Icons.person_outline_rounded,
                                controller: _nameController,
                                hint: 'Enter your name',
                                isDark: isDark,
                                textColor: textColor,
                                subColor: subColor,
                              ),
                              _divider(isDark),
                              _readOnlyTile(
                                label: 'Email',
                                icon: Icons.email_outlined,
                                value: email,
                                isDark: isDark,
                                textColor: textColor,
                                subColor: subColor,
                              ),
                              _divider(isDark),
                              _fieldTile(
                                label: 'Age',
                                icon: Icons.cake_outlined,
                                controller: _ageController,
                                hint: 'e.g. 20',
                                keyboardType: TextInputType.number,
                                isDark: isDark,
                                textColor: textColor,
                                subColor: subColor,
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 20),

                        // ── Learning Preferences ───────────────────────────
                        _sectionHeader('LEARNING PREFERENCES', sectionHeaderColor),
                        const SizedBox(height: 10),
                        _settingsCard(
                          isDark: isDark,
                          cardBg: cardBg,
                          borderColor: borderColor,
                          child: Column(
                            children: [
                              _dropdownTile(
                                label: 'Role',
                                icon: Icons.school_outlined,
                                value: _selectedRole,
                                items: _roles,
                                isDark: isDark,
                                textColor: textColor,
                                subColor: subColor,
                                cardBg: cardBg,
                                onChanged: (v) =>
                                    setState(() => _selectedRole = v!),
                              ),
                              _divider(isDark),
                              _dropdownTile(
                                label: 'Learning Goal',
                                icon: Icons.track_changes_outlined,
                                value: _selectedGoal,
                                items: _goals,
                                isDark: isDark,
                                textColor: textColor,
                                subColor: subColor,
                                cardBg: cardBg,
                                onChanged: (v) =>
                                    setState(() => _selectedGoal = v!),
                              ),
                              if (_selectedGoal == 'Other / Custom goal') ...[
                                _divider(isDark),
                                Padding(
                                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                                  child: TextField(
                                    controller: _customGoalController,
                                    style: TextStyle(
                                        color: textColor,
                                        fontFamily: 'Roboto',
                                        fontSize: 14),
                                    decoration: InputDecoration(
                                      hintText: 'Describe your learning purpose...',
                                      hintStyle: TextStyle(
                                          color: subColor, fontSize: 13),
                                      filled: true,
                                      fillColor: isDark
                                          ? const Color(0xFF252525)
                                          : const Color(0xFFF5F3EC),
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide.none,
                                      ),
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                              horizontal: 14, vertical: 12),
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),

                        const SizedBox(height: 20),

                        // ── App Preferences ────────────────────────────────
                        _sectionHeader('APP PREFERENCES', sectionHeaderColor),
                        const SizedBox(height: 10),
                        _settingsCard(
                          isDark: isDark,
                          cardBg: cardBg,
                          borderColor: borderColor,
                          child: Column(
                            children: [
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 16, vertical: 14),
                                child: Row(
                                  children: [
                                    Icon(Icons.palette_outlined,
                                        size: 20, color: const Color(0xFFD97706)),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text('Theme',
                                              style: TextStyle(
                                                fontFamily: 'Roboto',
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: textColor,
                                              )),
                                          Text('Choose your preferred look',
                                              style: TextStyle(
                                                  fontFamily: 'Roboto',
                                                  fontSize: 12,
                                                  color: subColor)),
                                        ],
                                      ),
                                    ),
                                    _buildThemeToggle(isDark),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 20),

                        // ── Account / Security ─────────────────────────────
                        _sectionHeader('ACCOUNT', sectionHeaderColor),
                        const SizedBox(height: 10),
                        _settingsCard(
                          isDark: isDark,
                          cardBg: cardBg,
                          borderColor: borderColor,
                          child: Column(
                            children: [
                              if (_isEmailUser) ...[
                                _actionTile(
                                  icon: Icons.lock_outline_rounded,
                                  label: 'Change Password',
                                  isDark: isDark,
                                  textColor: textColor,
                                  iconColor: const Color(0xFF5C67F2),
                                  onTap: () =>
                                      _showChangePasswordDialog(isDark),
                                ),
                                _divider(isDark),
                              ],
                              _actionTile(
                                icon: Icons.logout_rounded,
                                label: 'Sign Out',
                                isDark: isDark,
                                textColor: Colors.redAccent,
                                iconColor: Colors.redAccent,
                                onTap: () async {
                                  final nav = Navigator.of(context);
                                  await AuthService.instance.signOut();
                                  nav.pushReplacementNamed('/welcome');
                                },
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 40),

                        // ── Save Button (bottom) ───────────────────────────
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: ElevatedButton.icon(
                            onPressed: _isSaving ? null : _handleSave,
                            icon: _isSaving
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                        color: Colors.white, strokeWidth: 2))
                                : const Icon(Icons.check_rounded, size: 20),
                            label: Text(
                              _isSaving ? 'Saving...' : 'Save Changes',
                              style: const TextStyle(
                                fontFamily: 'Roboto',
                                fontWeight: FontWeight.w700,
                                fontSize: 15,
                              ),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFD97706),
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(26)),
                              elevation: 0,
                            ),
                          ),
                        ),

                        const SizedBox(height: 32),
                      ],
                    ),
                  ),
                ),
              ),
            ),
    );
  }

  // ── Theme Toggle (Cream / Dark / System) ──────────────────────────────────
  Widget _buildThemeToggle(bool isDark) {
    final modes = [
      {'key': 'cream', 'icon': Icons.light_mode_rounded, 'mode': ThemeMode.light},
      {'key': 'dark', 'icon': Icons.dark_mode_rounded, 'mode': ThemeMode.dark},
      {'key': 'system', 'icon': Icons.brightness_auto_rounded, 'mode': ThemeMode.system},
    ];

    return ListenableBuilder(
      listenable: themeController,
      builder: (_, __) {
        final liveLabel = themeController.themeLabel;
        return Container(
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF0EDE4),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: modes.map((m) {
              final isSelected = liveLabel == m['key'];
              return GestureDetector(
                onTap: () =>
                    themeController.setThemeMode(m['mode'] as ThemeMode),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? const Color(0xFFD97706)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Icon(
                    m['icon'] as IconData,
                    size: 18,
                    color: isSelected
                        ? Colors.white
                        : (isDark ? Colors.white38 : AppColors.inkFaint),
                  ),
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  Widget _sectionHeader(String title, Color color) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        title,
        style: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: color,
          letterSpacing: 1.1,
        ),
      ),
    );
  }

  Widget _settingsCard({
    required bool isDark,
    required Color cardBg,
    required Color borderColor,
    required Widget child,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: borderColor),
      ),
      child: child,
    );
  }

  Widget _divider(bool isDark) {
    return Divider(
      height: 1,
      indent: 16,
      endIndent: 16,
      color: isDark ? const Color(0xFF2E2E2C) : AppColors.border,
    );
  }

  Widget _fieldTile({
    required String label,
    required IconData icon,
    required TextEditingController controller,
    required String hint,
    required bool isDark,
    required Color textColor,
    required Color subColor,
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        children: [
          Icon(icon, size: 20, color: const Color(0xFFD97706)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: TextStyle(
                        fontFamily: 'Roboto',
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: subColor,
                        letterSpacing: 0.4)),
                const SizedBox(height: 4),
                TextField(
                  controller: controller,
                  keyboardType: keyboardType,
                  style: TextStyle(
                      color: textColor,
                      fontFamily: 'Roboto',
                      fontSize: 15,
                      fontWeight: FontWeight.w500),
                  decoration: InputDecoration(
                    hintText: hint,
                    hintStyle: TextStyle(color: subColor, fontSize: 14),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _readOnlyTile({
    required String label,
    required IconData icon,
    required String value,
    required bool isDark,
    required Color textColor,
    required Color subColor,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        children: [
          Icon(icon, size: 20, color: const Color(0xFFD97706)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: TextStyle(
                        fontFamily: 'Roboto',
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: subColor,
                        letterSpacing: 0.4)),
                const SizedBox(height: 4),
                Text(
                  value.isNotEmpty ? value : '—',
                  style: TextStyle(
                      color: textColor,
                      fontFamily: 'Roboto',
                      fontSize: 15,
                      fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: isDark
                  ? const Color(0xFF2A2A2A)
                  : const Color(0xFFF0EDE4),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'Verified',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF2D6A4F),
                fontFamily: 'Roboto',
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _dropdownTile({
    required String label,
    required IconData icon,
    required String value,
    required List<String> items,
    required bool isDark,
    required Color textColor,
    required Color subColor,
    required Color cardBg,
    required ValueChanged<String?> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
      child: Row(
        children: [
          Icon(icon, size: 20, color: const Color(0xFFD97706)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: TextStyle(
                        fontFamily: 'Roboto',
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: subColor,
                        letterSpacing: 0.4)),
                const SizedBox(height: 2),
                DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: value,
                    isExpanded: true,
                    dropdownColor: cardBg,
                    style: TextStyle(
                        color: textColor,
                        fontFamily: 'Roboto',
                        fontSize: 14,
                        fontWeight: FontWeight.w500),
                    icon: Icon(Icons.keyboard_arrow_down_rounded,
                        size: 18,
                        color: isDark ? Colors.white38 : AppColors.inkFaint),
                    isDense: true,
                    items: items
                        .map((item) => DropdownMenuItem(
                              value: item,
                              child: Text(item,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                      color: textColor,
                                      fontFamily: 'Roboto',
                                      fontSize: 14)),
                            ))
                        .toList(),
                    onChanged: onChanged,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionTile({
    required IconData icon,
    required String label,
    required bool isDark,
    required Color textColor,
    required Color iconColor,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Icon(icon, size: 20, color: iconColor),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(
                fontFamily: 'Roboto',
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: textColor,
              ),
            ),
            const Spacer(),
            Icon(Icons.chevron_right_rounded,
                size: 18,
                color: isDark ? Colors.white24 : AppColors.inkFaint),
          ],
        ),
      ),
    );
  }
}
