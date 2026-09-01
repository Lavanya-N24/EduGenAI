import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../main.dart' show AppColors;
import '../widgets/video_player.dart';

class ResultScreen extends StatefulWidget {
  final Map<String, dynamic>? initialData;

  const ResultScreen({
    super.key,
    this.initialData,
  });

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  Map<String, dynamic>? _data;
  int _selectedTab = 0; // 0 = Video Lesson, 1 = Study Notes (Text)

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();

    if (_data == null) {
      final args = ModalRoute.of(context)?.settings.arguments;

      if (args is Map<String, dynamic>) {
        _data = args;
      } else {
        _data = widget.initialData;
      }
    }
  }

  // ------------------------------------------------------------
  // VIDEO URL RESOLVER
  // ------------------------------------------------------------

  String? _getVideoUrl() {
    final data = _data;
    if (data == null) return null;

    final videoObj = data['video'];

    if (videoObj is Map) {
      final url = videoObj['url'];
      if (url != null && url.toString().trim().isNotEmpty) {
        return url.toString();
      }

      final filename = videoObj['filename'];
      if (filename != null && filename.toString().trim().isNotEmpty) {
        return _buildVideoUrl(filename.toString());
      }

      final videoPath = videoObj['video_path'];
      if (videoPath != null && videoPath.toString().trim().isNotEmpty) {
        return _convertBackendPathToUrl(videoPath.toString());
      }
    }

    final directUrl = data['video_url'];
    if (directUrl != null && directUrl.toString().trim().isNotEmpty) {
      return directUrl.toString();
    }

    final camelUrl = data['videoUrl'];
    if (camelUrl != null && camelUrl.toString().trim().isNotEmpty) {
      return camelUrl.toString();
    }

    return null;
  }

  String _buildVideoUrl(String filename) {
    return 'http://127.0.0.1:8000/videos/${Uri.encodeComponent(filename)}';
  }

  String _convertBackendPathToUrl(String path) {
    final normalized = path.replaceAll('\\', '/');
    if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
      return normalized;
    }
    final filename = normalized.split('/').last;
    return _buildVideoUrl(filename);
  }

  // ------------------------------------------------------------
  // COPY FULL TEXT TO CLIPBOARD
  // ------------------------------------------------------------

  void _copyNotesToClipboard(String title, String summary, List scenes, String? wikiExtract) {
    final StringBuffer buffer = StringBuffer();
    buffer.writeln('📚 $title - Study Notes (EduGenAI)\n');
    if (summary.isNotEmpty) {
      buffer.writeln('📝 Overview:\n$summary\n');
    }
    if (wikiExtract != null && wikiExtract.isNotEmpty) {
      buffer.writeln('📖 Wikipedia Background:\n$wikiExtract\n');
    }
    buffer.writeln('---');
    for (int i = 0; i < scenes.length; i++) {
      final s = scenes[i];
      final stitle = s['title'] ?? 'Section ${i + 1}';
      final text = s['narration'] ?? s['text'] ?? '';
      final eq = s['equation'] ?? '';
      buffer.writeln('${i + 1}. $stitle');
      buffer.writeln(text);
      if (eq.isNotEmpty) {
        buffer.writeln('Formula: $eq');
      }
      buffer.writeln('');
    }

    Clipboard.setData(ClipboardData(text: buffer.toString()));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('📋 Study notes copied to clipboard!'),
        behavior: SnackBarBehavior.floating,
        duration: Duration(seconds: 2),
      ),
    );
  }

  // ------------------------------------------------------------
  // BUILD
  // ------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : AppColors.cream;
    final cardBg = isDark ? const Color(0xFF222222) : Colors.white;
    final borderColor = isDark ? const Color(0x1FFFFFFF) : AppColors.border;

    final scenesRaw = _data?['scenes'];
    final List scenes = scenesRaw is List
        ? scenesRaw
        : (scenesRaw is Map ? (scenesRaw['scenes'] as List? ?? []) : []);

    final topic = _data?['topic'] ??
        _data?['title'] ??
        (scenesRaw is Map
            ? (scenesRaw['title'] ?? scenesRaw['topic'])
            : null) ??
        'Generated Lesson';

    final summary = (scenesRaw is Map ? scenesRaw['summary'] : null) ??
        _data?['summary'] ??
        '';

    final wikiData = _data?['wikipedia'];
    final String? wikiExtract = wikiData is Map ? wikiData['extract'] : null;
    final String? wikiUrl = wikiData is Map ? wikiData['url'] : null;

    final String? videoUrl = _getVideoUrl();

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        title: Text(
          topic.toString(),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            tooltip: 'Ask AI Tutor',
            icon: const Icon(Icons.school_outlined),
            onPressed: () {
              Navigator.pushNamed(context, '/tutor', arguments: _data);
            },
          ),
          IconButton(
            tooltip: 'Take Quiz',
            icon: const Icon(Icons.quiz_outlined),
            onPressed: () {
              Navigator.pushNamed(context, '/quiz', arguments: _data);
            },
          ),
          IconButton(
            tooltip: 'History',
            icon: const Icon(Icons.history_rounded),
            onPressed: () {
              Navigator.pushNamed(context, '/history');
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ------------------------------------------------------
                // 1. TOP MODE SWITCHER (Video vs Read Notes)
                // ------------------------------------------------------
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF2C2C2C) : const Color(0xFFEBE5D8),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: InkWell(
                          onTap: () => setState(() => _selectedTab = 0),
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: _selectedTab == 0
                                  ? (isDark ? const Color(0xFF1E1E1D) : Colors.white)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(10),
                              boxShadow: _selectedTab == 0
                                  ? [
                                      BoxShadow(
                                        color: Colors.black.withValues(alpha: 0.08),
                                        blurRadius: 4,
                                        offset: const Offset(0, 2),
                                      )
                                    ]
                                  : null,
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.play_circle_filled_rounded,
                                  size: 18,
                                  color: _selectedTab == 0
                                      ? const Color(0xFFD97706)
                                      : (isDark ? Colors.white54 : AppColors.inkSoft),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  '🎬 Watch Video Lesson',
                                  style: TextStyle(
                                    fontWeight: _selectedTab == 0
                                        ? FontWeight.bold
                                        : FontWeight.normal,
                                    fontSize: 13,
                                    color: _selectedTab == 0
                                        ? (isDark ? Colors.white : AppColors.ink)
                                        : (isDark ? Colors.white54 : AppColors.inkSoft),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: InkWell(
                          onTap: () => setState(() => _selectedTab = 1),
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: _selectedTab == 1
                                  ? (isDark ? const Color(0xFF1E1E1D) : Colors.white)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(10),
                              boxShadow: _selectedTab == 1
                                  ? [
                                      BoxShadow(
                                        color: Colors.black.withValues(alpha: 0.08),
                                        blurRadius: 4,
                                        offset: const Offset(0, 2),
                                      )
                                    ]
                                  : null,
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.menu_book_rounded,
                                  size: 18,
                                  color: _selectedTab == 1
                                      ? const Color(0xFF2D6A4F)
                                      : (isDark ? Colors.white54 : AppColors.inkSoft),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  '📖 Read Study Notes',
                                  style: TextStyle(
                                    fontWeight: _selectedTab == 1
                                        ? FontWeight.bold
                                        : FontWeight.normal,
                                    fontSize: 13,
                                    color: _selectedTab == 1
                                        ? (isDark ? Colors.white : AppColors.ink)
                                        : (isDark ? Colors.white54 : AppColors.inkSoft),
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

                const SizedBox(height: 16),

                // ------------------------------------------------------
                // 2. TAB CONTENT
                // ------------------------------------------------------
                if (_selectedTab == 0) ...[
                  // 🎬 VIDEO LESSON VIEW
                  _buildVideoLessonView(
                    context: context,
                    isDark: isDark,
                    cardBg: cardBg,
                    borderColor: borderColor,
                    topic: topic.toString(),
                    videoUrl: videoUrl,
                    scenes: scenes,
                  ),
                ] else ...[
                  // 📖 CHATGPT-STYLE STUDY NOTES VIEW
                  _buildStudyNotesView(
                    context: context,
                    isDark: isDark,
                    cardBg: cardBg,
                    borderColor: borderColor,
                    topic: topic.toString(),
                    summary: summary.toString(),
                    wikiExtract: wikiExtract,
                    wikiUrl: wikiUrl,
                    scenes: scenes,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------
  // 🎬 VIDEO LESSON VIEW WIDGET
  // ------------------------------------------------------------
  Widget _buildVideoLessonView({
    required BuildContext context,
    required bool isDark,
    required Color cardBg,
    required Color borderColor,
    required String topic,
    required String? videoUrl,
    required List scenes,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Metadata Chips
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF5C67F2).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                '🎬 ${scenes.length} Scenes',
                style: const TextStyle(
                  color: Color(0xFF5C67F2),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Text(
                '⏱️ Multi-Scene Lesson',
                style: TextStyle(
                  color: Color(0xFF0284C7),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 16),

        // Video Player Box
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Container(
            width: double.infinity,
            color: Colors.black,
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: videoUrl != null
                  ? EduVideoPlayer(
                      videoUrl: videoUrl,
                      title: topic,
                    )
                  : Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.video_library_rounded,
                              size: 48, color: Colors.white38),
                          const SizedBox(height: 10),
                          Text(
                            topic,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600,
                                fontSize: 16),
                          ),
                          const SizedBox(height: 8),
                          const Text('Video rendering...',
                              style: TextStyle(color: Colors.white54, fontSize: 12)),
                        ],
                      ),
                    ),
            ),
          ),
        ),

        const SizedBox(height: 18),

        // Interactive Action Buttons
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/quiz', arguments: _data);
                  },
                  icon: const Icon(Icons.quiz_outlined, size: 18),
                  label: const Text('Take Smart Quiz'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2D6A4F),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(24)),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/tutor', arguments: _data);
                  },
                  icon: const Icon(Icons.school_outlined, size: 18),
                  label: const Text('Ask AI Tutor'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF5C67F2),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(24)),
                  ),
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 28),

        // Scene Storyboard Section
        const Text(
          '🎬 Scene-by-Scene Storyboard',
          style: TextStyle(
            fontFamily: 'Georgia',
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),

        if (scenes.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: cardBg,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: borderColor),
            ),
            child: const Center(
              child: Text('No scenes available.'),
            ),
          )
        else
          ...List.generate(scenes.length, (index) {
            final scene = scenes[index];
            final sceneTitle = scene['title'] ?? 'Scene ${index + 1}';
            final narration = scene['narration'] ?? scene['text'] ?? '';
            final transition = scene['transition_explanation'] ?? '';
            final equation = scene['equation'] ?? '';

            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: cardBg,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: borderColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFD97706).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          'Scene ${index + 1}',
                          style: const TextStyle(
                            color: Color(0xFFD97706),
                            fontWeight: FontWeight.bold,
                            fontSize: 11,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          sceneTitle,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (transition.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: isDark
                            ? const Color(0xFF2B2822)
                            : const Color(0xFFFFFBEB),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(0xFFD97706).withValues(alpha: 0.3),
                        ),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.arrow_forward_rounded,
                              size: 14, color: Color(0xFFD97706)),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              transition,
                              style: TextStyle(
                                fontSize: 12,
                                color: isDark
                                    ? const Color(0xFFFDE68A)
                                    : const Color(0xFF92400E),
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(
                    narration,
                    style: TextStyle(
                      color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                      height: 1.4,
                      fontSize: 14,
                    ),
                  ),
                  if (equation.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF5C67F2).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '🧪 Formula: $equation',
                        style: const TextStyle(
                          color: Color(0xFF5C67F2),
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            );
          }),
      ],
    );
  }

  // ------------------------------------------------------------
  // 📖 CHATGPT-STYLE STUDY NOTES VIEW WIDGET
  // ------------------------------------------------------------
  Widget _buildStudyNotesView({
    required BuildContext context,
    required bool isDark,
    required Color cardBg,
    required Color borderColor,
    required String topic,
    required String summary,
    required String? wikiExtract,
    required String? wikiUrl,
    required List scenes,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Top Article Header Info
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF2D6A4F).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Text(
                '📖 Complete Text Guide',
                style: TextStyle(
                  color: Color(0xFF2D6A4F),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFFD97706).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                '⏱️ ~${(scenes.length * 0.5).ceil()} min read',
                style: const TextStyle(
                  color: Color(0xFFD97706),
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const Spacer(),
            // Copy Notes Button
            OutlinedButton.icon(
              onPressed: () => _copyNotesToClipboard(topic, summary, scenes, wikiExtract),
              icon: const Icon(Icons.copy_rounded, size: 15),
              label: const Text('Copy Notes', style: TextStyle(fontSize: 12)),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
              ),
            ),
          ],
        ),

        const SizedBox(height: 16),

        // Main Title Header
        Text(
          topic,
          style: TextStyle(
            fontFamily: 'Georgia',
            fontSize: 26,
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.white : AppColors.ink,
          ),
        ),
        const SizedBox(height: 8),

        // Overview / Definition Card
        if (summary.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E2620) : const Color(0xFFF0FDF4),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: const Color(0xFF2D6A4F).withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.lightbulb_rounded,
                        size: 18, color: Color(0xFF2D6A4F)),
                    SizedBox(width: 8),
                    Text(
                      'Lesson Overview',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2D6A4F),
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  summary,
                  style: TextStyle(
                    fontSize: 14,
                    height: 1.5,
                    color: isDark ? const Color(0xFFD1FAE5) : const Color(0xFF14532D),
                  ),
                ),
              ],
            ),
          ),

        // Wikipedia Research Background Callout (if available)
        if (wikiExtract != null && wikiExtract.isNotEmpty) ...[
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1B232E) : const Color(0xFFF0F7FF),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: const Color(0xFF0284C7).withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.verified_rounded, size: 16, color: Color(0xFF0284C7)),
                    SizedBox(width: 6),
                    Text(
                      'Wikipedia Verified Background',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF0284C7),
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  wikiExtract,
                  style: TextStyle(
                    fontSize: 13,
                    height: 1.45,
                    color: isDark ? const Color(0xFFBAE6FD) : const Color(0xFF0369A1),
                  ),
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: 24),

        // Structured Breakdown Sections
        const Text(
          '📑 Step-by-Step Breakdown',
          style: TextStyle(
            fontFamily: 'Georgia',
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),

        ...List.generate(scenes.length, (index) {
          final s = scenes[index];
          final stitle = s['title'] ?? 'Section ${index + 1}';
          final text = s['narration'] ?? s['text'] ?? '';
          final transition = s['transition_explanation'] ?? '';
          final equation = s['equation'] ?? '';

          return Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: cardBg,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: borderColor),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Section Number + Title
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: const Color(0xFFD97706).withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          '${index + 1}',
                          style: const TextStyle(
                            color: Color(0xFFD97706),
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        stitle,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ],
                ),

                // Transition Context
                if (transition.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    '💡 Context: $transition',
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      fontSize: 12.5,
                      color: isDark ? const Color(0xFFFBBF24) : const Color(0xFFB45309),
                    ),
                  ),
                ],

                const SizedBox(height: 10),

                // Main Paragraph
                Text(
                  text,
                  style: TextStyle(
                    fontSize: 14.5,
                    height: 1.6,
                    color: isDark ? const Color(0xFFE2E8F0) : AppColors.ink,
                  ),
                ),

                // Equation Callout Badge
                if (equation.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF222038) : const Color(0xFFEEF2FF),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.4),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.calculate_outlined,
                            size: 18, color: Color(0xFF6366F1)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            equation,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                              color: Color(0xFF6366F1),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          );
        }),

        const SizedBox(height: 12),

        // Key Takeaways & Checklist Card
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: cardBg,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: borderColor),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.checklist_rounded,
                      size: 20, color: Color(0xFFD97706)),
                  SizedBox(width: 8),
                  Text(
                    'Key Takeaways Checklist',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              ...List.generate(scenes.length, (i) {
                final s = scenes[i];
                final stitle = s['title'] ?? 'Point ${i + 1}';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.check_circle_rounded,
                          size: 16, color: Color(0xFF2D6A4F)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          stitle,
                          style: TextStyle(
                            fontSize: 13.5,
                            color: isDark ? Colors.white70 : AppColors.ink,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ),
        ),

        const SizedBox(height: 24),

        // Bottom CTAs
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 50,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/quiz', arguments: _data);
                  },
                  icon: const Icon(Icons.quiz_outlined, size: 18),
                  label: const Text('Test Your Knowledge'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2D6A4F),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(25)),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 50,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pushNamed(context, '/tutor', arguments: _data);
                  },
                  icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
                  label: const Text('Ask EduBot a Question'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF5C67F2),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(25)),
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
