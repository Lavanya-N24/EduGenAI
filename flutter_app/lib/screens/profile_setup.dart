import 'package:flutter/material.dart';
import '../main.dart' show AppColors;
import '../services/auth_service.dart';

class ProfileSetupScreen extends StatefulWidget {
  const ProfileSetupScreen({super.key});

  @override
  State<ProfileSetupScreen> createState() => _ProfileSetupScreenState();
}

class _ProfileSetupScreenState extends State<ProfileSetupScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _ageController = TextEditingController();
  final TextEditingController _customGoalController = TextEditingController();

  String _selectedRole = 'Student';
  String _selectedGoal = 'Exam preparation & concept mastery';
  bool _isSaving = false;

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

  @override
  void initState() {
    super.initState();
    final user = AuthService.instance.currentUser;
    if (user != null && user.name.isNotEmpty && user.name != 'Learner') {
      _nameController.text = user.name;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _customGoalController.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    final name = _nameController.text.trim();
    final age = _ageController.text.trim();

    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your name')),
      );
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
        age: age.isNotEmpty ? age : 'Not specified',
        role: _selectedRole,
        goal: finalGoal,
      );

      if (mounted) {
        Navigator.pushReplacementNamed(context, '/theme-selector');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving profile: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF141413) : AppColors.cream;
    final cardBg = isDark ? const Color(0xFF1E1E1D) : Colors.white;

    return Scaffold(
      backgroundColor: bgColor,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Container(
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: isDark ? const Color(0xFF2E2E2C) : AppColors.border,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Center(
                    child: Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: const Color(0xFFD97706).withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.person_pin_rounded,
                          size: 28, color: Color(0xFFD97706)),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: Text(
                      'Tell us about yourself',
                      style: TextStyle(
                        fontFamily: 'Georgia',
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : AppColors.ink,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Center(
                    child: Text(
                      'Help us personalize your study animations & quizzes',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontFamily: 'Roboto',
                        fontSize: 13,
                        color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Name Field
                  const Text('Full Name', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      hintText: 'Enter your name',
                      prefixIcon: Icon(Icons.person_outline, size: 20),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Age Field
                  const Text('Age', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _ageController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      hintText: 'e.g. 20',
                      prefixIcon: Icon(Icons.cake_outlined, size: 20),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // What describes you best?
                  const Text('What describes you best?',
                      style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    value: _selectedRole,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.school_outlined, size: 20),
                    ),
                    dropdownColor: cardBg,
                    items: _roles.map((role) {
                      return DropdownMenuItem(
                        value: role,
                        child: Text(role, style: TextStyle(color: isDark ? Colors.white : AppColors.ink)),
                      );
                    }).toList(),
                    onChanged: (val) => setState(() => _selectedRole = val!),
                  ),
                  const SizedBox(height: 16),

                  // Why do you need EduGenAI?
                  const Text('Why are you using EduGenAI?',
                      style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String>(
                    value: _selectedGoal,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.track_changes_outlined, size: 20),
                    ),
                    dropdownColor: cardBg,
                    items: _goals.map((goal) {
                      return DropdownMenuItem(
                        value: goal,
                        child: Text(
                          goal,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: isDark ? Colors.white : AppColors.ink, fontSize: 13),
                        ),
                      );
                    }).toList(),
                    onChanged: (val) => setState(() => _selectedGoal = val!),
                  ),

                  if (_selectedGoal == 'Other / Custom goal') ...[
                    const SizedBox(height: 10),
                    TextField(
                      controller: _customGoalController,
                      decoration: const InputDecoration(
                        hintText: 'Describe your learning purpose...',
                      ),
                    ),
                  ],

                  const SizedBox(height: 28),

                  // Submit Button
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: _isSaving ? null : _handleSave,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFD97706),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : const Text(
                              'Continue →',
                              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
