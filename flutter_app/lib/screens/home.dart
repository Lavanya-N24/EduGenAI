import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../main.dart' show AppColors;
import '../services/api_service.dart';
import '../services/auth_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final TextEditingController _promptController = TextEditingController();

  String? _attachedFileName;
  Uint8List? _attachedFileBytes;
  
  // ── Learning Level State (Basic, Beginner, Advanced) ──
  String _selectedLevelKey = 'beginner';
  String _selectedLevelLabel = 'Beginner';

  final List<Map<String, String>> _levels = [
    {
      'key': 'basic',
      'label': 'Basic',
      'icon': '🌱',
      'desc': 'Simple summaries & fundamental concepts'
    },
    {
      'key': 'beginner',
      'label': 'Beginner',
      'icon': '📘',
      'desc': 'Balanced explanations with clear examples'
    },
    {
      'key': 'advanced',
      'label': 'Advanced',
      'icon': '🔥',
      'desc': 'In-depth technical breakdown & detailed theory'
    },
  ];

  String _targetLanguage = 'en';
  String _targetLanguageLabel = '🌐 English';
  bool _isListening = false;

  // ── 15-language list ──────────────────────────────────────────────────────
  final List<Map<String, String>> _languages = [
    // Indian Languages
    {'code': 'kn', 'label': 'Kannada', 'native': 'ಕನ್ನಡ', 'flag': '🇮🇳'},
    {'code': 'hi', 'label': 'Hindi',   'native': 'हिन्दी',  'flag': '🇮🇳'},
    {'code': 'te', 'label': 'Telugu',  'native': 'తెలుగు',  'flag': '🇮🇳'},
    {'code': 'ta', 'label': 'Tamil',   'native': 'தமிழ்',   'flag': '🇮🇳'},
    {'code': 'ml', 'label': 'Malayalam','native': 'മലയാളം', 'flag': '🇮🇳'},
    {'code': 'bn', 'label': 'Bengali', 'native': 'বাংলা',   'flag': '🇮🇳'},
    {'code': 'gu', 'label': 'Gujarati','native': 'ગુજરાતી', 'flag': '🇮🇳'},
    {'code': 'mr', 'label': 'Marathi', 'native': 'मराठी',   'flag': '🇮🇳'},
    {'code': 'ur', 'label': 'Urdu',    'native': 'اردو',    'flag': '🇵🇰'},
    // Global Languages
    {'code': 'en', 'label': 'English',  'native': 'English',   'flag': '🌐'},
    {'code': 'ja', 'label': 'Japanese', 'native': '日本語',      'flag': '🇯🇵'},
    {'code': 'ar', 'label': 'Arabic',   'native': 'العربية',    'flag': '🇸🇦'},
    {'code': 'es', 'label': 'Spanish',  'native': 'Español',    'flag': '🇪🇸'},
    {'code': 'fr', 'label': 'French',   'native': 'Français',   'flag': '🇫🇷'},
    {'code': 'de', 'label': 'German',   'native': 'Deutsch',    'flag': '🇩🇪'},
  ];

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'docx', 'pptx', 'txt', 'png', 'jpg', 'jpeg'],
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        _attachedFileName = result.files.single.name;
        _attachedFileBytes = result.files.single.bytes;
      });
    }
  }

  // ── Level Selection Bottom Sheet ──
  void _showLevelPicker(bool isDark) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        final sheetBg = isDark ? const Color(0xFF1E1E1E) : Colors.white;
        final textColor = isDark ? Colors.white : AppColors.ink;

        return Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          decoration: BoxDecoration(
            color: sheetBg,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDark ? Colors.white12 : AppColors.border,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Text(
                  'Select Learning Level',
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: textColor,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              ..._levels.map((lvl) {
                final isSelected = _selectedLevelKey == lvl['key'];
                return Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? (isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF3EFE6))
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: ListTile(
                    dense: true,
                    leading: Text(lvl['icon']!, style: const TextStyle(fontSize: 22)),
                    title: Text(
                      lvl['label']!,
                      style: TextStyle(
                        fontFamily: 'Roboto',
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: textColor,
                      ),
                    ),
                    subtitle: Text(
                      lvl['desc']!,
                      style: TextStyle(
                        fontFamily: 'Roboto',
                        fontSize: 12,
                        color: isDark ? Colors.white60 : AppColors.inkSoft,
                      ),
                    ),
                    trailing: isSelected
                        ? const Icon(Icons.check_circle_rounded, color: Color(0xFFD97706))
                        : null,
                    onTap: () {
                      setState(() {
                        _selectedLevelKey = lvl['key']!;
                        _selectedLevelLabel = lvl['label']!;
                      });
                      Navigator.pop(context);
                    },
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }

  // ── Language Selection Bottom Sheet ──
  void _showLanguagePicker(bool isDark) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) {
        final sheetBg = isDark ? const Color(0xFF1E1E1E) : Colors.white;
        final textColor = isDark ? Colors.white : AppColors.ink;

        return Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          decoration: BoxDecoration(
            color: sheetBg,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDark ? Colors.white12 : AppColors.border,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Text(
                  'Select Output Language',
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: textColor,
                  ),
                ),
              ),
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'Video narration, subtitles and TTS will be in the selected language.',
                  style: TextStyle(
                    fontFamily: 'Roboto',
                    fontSize: 12,
                    color: isDark ? Colors.white54 : AppColors.inkSoft,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(ctx).size.height * 0.5,
                ),
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _languages.length,
                  itemBuilder: (_, i) {
                    final lang = _languages[i];
                    final isSelected = _targetLanguage == lang['code'];
                    // Section divider between Indian and Global
                    final showDivider = i == 9;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (showDivider) ...[
                          const SizedBox(height: 4),
                          Divider(color: isDark ? Colors.white12 : AppColors.border, height: 1),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(8, 10, 8, 2),
                            child: Text(
                              'Global Languages',
                              style: TextStyle(
                                fontFamily: 'Roboto',
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white38 : AppColors.inkSoft,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ),
                        ] else if (i == 0)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(8, 0, 8, 6),
                            child: Text(
                              'Indian Languages',
                              style: TextStyle(
                                fontFamily: 'Roboto',
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white38 : AppColors.inkSoft,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ),
                        Container(
                          margin: const EdgeInsets.symmetric(vertical: 2),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? (isDark
                                    ? const Color(0xFF2C2C2C)
                                    : const Color(0xFFF3EFE6))
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: ListTile(
                            dense: true,
                            leading: Text(
                              lang['flag']!,
                              style: const TextStyle(fontSize: 22),
                            ),
                            title: Text(
                              lang['label']!,
                              style: TextStyle(
                                fontFamily: 'Roboto',
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                                color: textColor,
                              ),
                            ),
                            subtitle: Text(
                              lang['native']!,
                              style: TextStyle(
                                fontFamily: 'Roboto',
                                fontSize: 12,
                                color: isDark ? Colors.white54 : AppColors.inkSoft,
                              ),
                            ),
                            trailing: isSelected
                                ? const Icon(
                                    Icons.check_circle_rounded,
                                    color: Color(0xFFD97706),
                                  )
                                : null,
                            onTap: () {
                              setState(() {
                                _targetLanguage = lang['code']!;
                                _targetLanguageLabel =
                                    '${lang["flag"]!} ${lang["label"]!}';
                              });
                              Navigator.pop(ctx);
                            },
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _sendPrompt() async {
    final text = _promptController.text.trim();
    if (text.isEmpty && _attachedFileBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a topic or upload a file first'),
          backgroundColor: Colors.orangeAccent,
        ),
      );
      return;
    }

    // Loading Dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return Center(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 32),
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF222222) : Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: isDark ? Colors.white12 : AppColors.border,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.18),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 42,
                  height: 42,
                  child: CircularProgressIndicator(
                    color: Color(0xFFD97706),
                    strokeWidth: 3,
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  'Generating $_selectedLevelLabel Video...',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: isDark ? Colors.white : AppColors.ink,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Synthesizing script, generating scenes, and rendering audio.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Roboto',
                    fontSize: 13,
                    color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );

    try {
      final response = await ApiService.generateFullPipeline(
        text: text.isNotEmpty ? text : null,
        fileBytes: _attachedFileBytes,
        fileName: _attachedFileName,
        targetLanguage: _targetLanguage,
        learningMode: _selectedLevelKey, // Selected Level passed here
      );

      if (mounted) Navigator.of(context).pop();

      // Save to history
      final lessonTitle = response['title'] ?? response['topic'] ?? (text.isNotEmpty ? text : 'Lesson');
      await AuthService.instance.saveHistoryItem(
        title: lessonTitle,
        mode: _selectedLevelKey,
        generationData: response,
      );

      if (mounted) {
        Navigator.pushNamed(context, '/result', arguments: response);
      }
    } catch (e) {
      if (mounted) Navigator.of(context).pop();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Generation error: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  // ── Gemini-style Attachment Modal Sheet ──
  void _showAttachmentSheet(bool isDark) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) {
        final sheetBg = isDark ? const Color(0xFF1E1E1E) : Colors.white;
        final pillBg = isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF3EFE6);
        final textColor = isDark ? Colors.white : AppColors.ink;
        final subTextColor = isDark ? Colors.white60 : AppColors.inkSoft;

        return Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          decoration: BoxDecoration(
            color: sheetBg,
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: isDark ? Colors.white12 : AppColors.border,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildTopPill(
                      icon: Icons.attach_file_rounded,
                      label: 'Files',
                      pillBg: pillBg,
                      textColor: textColor,
                      onTap: () {
                        Navigator.pop(context);
                        _pickFile();
                      },
                    ),
                    const SizedBox(width: 14),
                    _buildTopPill(
                      icon: Icons.face_rounded,
                      label: 'Avatar',
                      pillBg: pillBg,
                      textColor: textColor,
                      onTap: () => Navigator.pop(context),
                    ),
                    const SizedBox(width: 14),
                    _buildTopPill(
                      icon: Icons.add_to_drive_rounded,
                      label: 'Drive',
                      pillBg: pillBg,
                      textColor: textColor,
                      onTap: () => Navigator.pop(context),
                    ),
                    const SizedBox(width: 14),
                    _buildTopPill(
                      icon: Icons.photo_library_outlined,
                      label: 'Photos',
                      pillBg: pillBg,
                      textColor: textColor,
                      onTap: () {
                        Navigator.pop(context);
                        _pickFile();
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              Divider(color: isDark ? Colors.white12 : AppColors.border, height: 1),
              const SizedBox(height: 10),
              _buildFeatureTile(
                icon: Icons.image_outlined,
                title: 'Images',
                subtitle: 'Upload diagrams, schematics, and notes',
                textColor: textColor,
                subTextColor: subTextColor,
                onTap: () {
                  Navigator.pop(context);
                  _pickFile();
                },
              ),
              _buildFeatureTile(
                icon: Icons.movie_creation_outlined,
                title: 'Videos',
                subtitle: 'Convert topic into animated video lesson',
                textColor: textColor,
                subTextColor: subTextColor,
                onTap: () => Navigator.pop(context),
              ),
              _buildFeatureTile(
                icon: Icons.music_note_outlined,
                title: 'Audio',
                subtitle: 'Generate podcasts and audio tracks',
                textColor: textColor,
                subTextColor: subTextColor,
                onTap: () => Navigator.pop(context),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTopPill({
    required IconData icon,
    required String label,
    required Color pillBg,
    required Color textColor,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(color: pillBg, shape: BoxShape.circle),
            child: Icon(icon, color: textColor, size: 24),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              fontFamily: 'Roboto',
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color textColor,
    required Color subTextColor,
    required VoidCallback onTap,
  }) {
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: const Color(0xFFD97706).withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: const Color(0xFFD97706), size: 22),
      ),
      title: Text(
        title,
        style: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 15,
          fontWeight: FontWeight.w700,
          color: textColor,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: TextStyle(fontFamily: 'Roboto', fontSize: 12, color: subTextColor),
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : const Color(0xFFFAF9F5);
    final cardColor = isDark ? const Color(0xFF222222) : Colors.white;

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: bgColor,
      drawer: _buildSketchDrawer(isDark),
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: Icon(
                      Icons.menu_rounded,
                      size: 26,
                      color: isDark ? Colors.white70 : const Color(0xFF333333),
                    ),
                    onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                  ),
                  Text(
                    'EduGenAI',
                    style: TextStyle(
                      fontFamily: 'Georgia',
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: isDark ? Colors.white : AppColors.ink,
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),

            // Center Content
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 720),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF2E2E2E) : const Color(0xFFF0ECE1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.auto_awesome,
                            size: 30,
                            color: Color(0xFFD97706),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Upload notes, PDFs or enter a topic',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: 'Georgia',
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Transform text or documents into animated video lessons and smart quizzes.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 13,
                            color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Quick suggestion pills
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          alignment: WrapAlignment.center,
                          children: [
                            _buildSuggestionChip('🌱 Photosynthesis', isDark),
                            _buildSuggestionChip('⚡ Newton\'s Laws', isDark),
                            _buildSuggestionChip('🧬 DNA Replication', isDark),
                            _buildSuggestionChip('🪐 Solar System', isDark),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // Bottom Prompt Container (Centred and constrained with safe bottom padding)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Container(
                  decoration: BoxDecoration(
                    color: cardColor,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: isDark ? Colors.white12 : const Color(0xFFE5E2D9),
                      width: 1.2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.04),
                        blurRadius: 16,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (_attachedFileName != null)
                        Padding(
                          padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: isDark ? Colors.white10 : const Color(0xFFEFEBE0),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.attach_file, size: 14),
                                    const SizedBox(width: 4),
                                    Text(_attachedFileName!, style: const TextStyle(fontSize: 12)),
                                    const SizedBox(width: 4),
                                    GestureDetector(
                                      onTap: () => setState(() {
                                        _attachedFileName = null;
                                        _attachedFileBytes = null;
                                      }),
                                      child: const Icon(Icons.close, size: 14),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),

                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        child: TextField(
                          controller: _promptController,
                          maxLines: 4,
                          minLines: 1,
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 15,
                            color: isDark ? Colors.white : const Color(0xFF1E1E1E),
                          ),
                          decoration: InputDecoration(
                            hintText: 'Ask EduGenAI or enter topic...',
                            hintStyle: TextStyle(
                              fontFamily: 'Roboto',
                              color: isDark ? Colors.white38 : const Color(0xFF9E9E9E),
                            ),
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(vertical: 10),
                          ),
                        ),
                      ),

                      Padding(
                        padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
                        child: Row(
                          children: [
                            // (+) Attachment icon
                            IconButton(
                              icon: Icon(
                                Icons.add_circle_outline_rounded,
                                size: 26,
                                color: isDark ? Colors.white70 : const Color(0xFF444444),
                              ),
                              onPressed: () => _showAttachmentSheet(isDark),
                            ),

                            // ── Level Selector Chip ──
                            GestureDetector(
                              onTap: () => _showLevelPicker(isDark),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: isDark ? const Color(0xFF2C2C2C) : const Color(0xFFEFEBE0),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: isDark ? Colors.white10 : AppColors.border,
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      _selectedLevelLabel,
                                      style: TextStyle(
                                        fontFamily: 'Roboto',
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: isDark ? Colors.white70 : const Color(0xFF444444),
                                      ),
                                    ),
                                    const SizedBox(width: 4),
                                    Icon(
                                      Icons.keyboard_arrow_down_rounded,
                                      size: 16,
                                      color: isDark ? Colors.white54 : const Color(0xFF666666),
                                    ),
                                  ],
                                ),
                              ),
                            ),

                            const SizedBox(width: 6),

                            // ── Language Selector Chip ──
                            GestureDetector(
                              onTap: () => _showLanguagePicker(isDark),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: _targetLanguage == 'en'
                                      ? (isDark ? const Color(0xFF2C2C2C) : const Color(0xFFEFEBE0))
                                      : (isDark ? const Color(0xFF1A2A1A) : const Color(0xFFE8F5E9)),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: _targetLanguage == 'en'
                                        ? (isDark ? Colors.white10 : AppColors.border)
                                        : const Color(0xFF4CAF50).withValues(alpha: 0.4),
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      _targetLanguageLabel,
                                      style: TextStyle(
                                        fontFamily: 'Roboto',
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: _targetLanguage == 'en'
                                            ? (isDark ? Colors.white70 : const Color(0xFF444444))
                                            : const Color(0xFF2E7D32),
                                      ),
                                    ),
                                    const SizedBox(width: 4),
                                    Icon(
                                      Icons.keyboard_arrow_down_rounded,
                                      size: 16,
                                      color: _targetLanguage == 'en'
                                          ? (isDark ? Colors.white54 : const Color(0xFF666666))
                                          : const Color(0xFF2E7D32),
                                    ),
                                  ],
                                ),
                              ),
                            ),

                            const Spacer(),

                            // Microphone Voice Button
                            IconButton(
                              icon: Icon(
                                _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                                size: 24,
                                color: _isListening
                                    ? Colors.redAccent
                                    : (isDark ? Colors.white70 : const Color(0xFF444444)),
                              ),
                              onPressed: () {
                                setState(() => _isListening = !_isListening);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      _isListening ? 'Listening...' : 'Voice input stopped',
                                    ),
                                    duration: const Duration(seconds: 1),
                                  ),
                                );
                              },
                            ),

                            const SizedBox(width: 4),

                            // Send / Generate Button
                            GestureDetector(
                              onTap: _sendPrompt,
                              child: Container(
                                width: 38,
                                height: 38,
                                decoration: BoxDecoration(
                                  color: isDark ? const Color(0xFF2563EB) : const Color(0xFF1D4ED8),
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(
                                  Icons.check_rounded,
                                  size: 22,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionChip(String label, bool isDark) {
    return ActionChip(
      label: Text(
        label,
        style: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 12,
          color: isDark ? Colors.white70 : const Color(0xFF444444),
          fontWeight: FontWeight.w500,
        ),
      ),
      backgroundColor: isDark ? const Color(0xFF222222) : const Color(0xFFF3EFE6),
      side: BorderSide(
        color: isDark ? Colors.white10 : AppColors.border,
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      onPressed: () {
        final cleanText = label.replaceAll(RegExp(r'^[^\w]+'), '').trim();
        _promptController.text = cleanText;
      },
    );
  }

  // ── Side Navigation Drawer ──
  Widget _buildSketchDrawer(bool isDark) {
    final user = AuthService.instance.currentUser;
    final userName = user?.name ?? 'Learner';
    final drawerBg = isDark ? const Color(0xFF1E1E1E) : const Color(0xFFF7F5EE);

    return Drawer(
      backgroundColor: drawerBg,
      child: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(20),
              child: InkWell(
                onTap: () {
                  Navigator.pop(context);
                  Navigator.pushNamed(context, '/profile-settings');
                },
                borderRadius: BorderRadius.circular(12),
                child: Row(
                  children: [
                    Hero(
                      tag: 'profile_avatar',
                      child: CircleAvatar(
                        backgroundColor: const Color(0xFFD97706),
                        child: Text(
                          userName.isNotEmpty ? userName[0].toUpperCase() : 'L',
                          style: const TextStyle(
                              color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            userName,
                            style: const TextStyle(
                                fontWeight: FontWeight.w700, fontSize: 16),
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            'View profile',
                            style: TextStyle(
                              fontSize: 12,
                              fontFamily: 'Roboto',
                              color: isDark
                                  ? Colors.white38
                                  : AppColors.inkFaint,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      size: 18,
                      color: isDark ? Colors.white24 : AppColors.inkFaint,
                    ),
                  ],
                ),
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                children: [
                  // Profile tile
                  _drawerTile(
                    icon: Icons.manage_accounts_outlined,
                    label: 'Profile',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/profile-settings');
                    },
                  ),
                  _drawerTile(
                    icon: Icons.video_collection_outlined,
                    label: 'Text to Vid',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/result');
                    },
                  ),
                  _drawerTile(
                    icon: Icons.psychology_outlined,
                    label: 'AI Tutor',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/tutor');
                    },
                  ),
                  _drawerTile(
                    icon: Icons.quiz_outlined,
                    label: 'Quiz',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/quiz');
                    },
                  ),
                  _drawerTile(
                    icon: Icons.insights_outlined,
                    label: 'Analytics',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/analytics');
                    },
                  ),
                  _drawerTile(
                    icon: Icons.history_edu_outlined,
                    label: 'History',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/history');
                    },
                  ),
                  const Divider(height: 24),
                  _drawerTile(
                    icon: Icons.settings_outlined,
                    label: 'Appearance',
                    onTap: () {
                      Navigator.pop(context);
                      Navigator.pushNamed(context, '/theme-selector');
                    },
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: ListTile(
                leading: const Icon(Icons.logout_rounded, color: Colors.redAccent),
                title: const Text('Sign Out', style: TextStyle(color: Colors.redAccent)),
                onTap: () async {
                  await AuthService.instance.signOut();
                  if (mounted) {
                    Navigator.pushReplacementNamed(context, '/welcome');
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _drawerTile({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ListTile(
      dense: true,
      leading: Icon(icon, size: 22, color: const Color(0xFF6B5E4D)),
      title: Text(
        label,
        style: const TextStyle(
          fontFamily: 'Roboto',
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      onTap: onTap,
    );
  }
}