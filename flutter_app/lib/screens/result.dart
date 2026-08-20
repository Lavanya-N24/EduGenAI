import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../widgets/video_player.dart';
import '../services/api_service.dart';

class ResultScreen extends StatefulWidget {
  const ResultScreen({super.key});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  bool _isSharing = false;
  String? _shareUrl;

  Future<void> _createShareLink(Map<String, dynamic> video, String title) async {
    setState(() => _isSharing = true);
    try {
      final result = await ApiService.createShareLink(
        userId: 'default_user',
        filename: video['filename'],
        title: title,
        duration: (video['duration'] ?? 0).toDouble(),
      );
      final url = result['share_url'] ?? '';
      setState(() => _shareUrl = url);
      await Clipboard.setData(ClipboardData(text: url));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('🔗 Share link copied!\n$url'),
            backgroundColor: const Color(0xFF4ECDC4),
            duration: const Duration(seconds: 4),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Share failed: $e'), backgroundColor: Colors.redAccent),
        );
      }
    } finally {
      if (mounted) setState(() => _isSharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result =
        ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;

    if (result == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Result')),
        body: const Center(child: Text('No result data')),
      );
    }

    final scenes     = result['scenes'] ?? {};
    final sceneList  = (scenes['scenes'] as List?) ?? [];
    final video      = result['video'] as Map<String, dynamic>?;
    final subtitle   = result['subtitle'] as Map<String, dynamic>?;
    final title      = scenes['title'] ?? 'Generated Result';
    final mode       = (scenes['learning_mode'] ?? 'beginner') as String;
    final content    = sceneList.isNotEmpty
        ? sceneList.map((s) => s['narration'] ?? '').join('\n\n')
        : '';

    final videoUrl = video != null
        ? '${ApiService.baseUrl}/outputs/video/${video['filename']}'
        : null;
    final downloadUrl = videoUrl;

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          IconButton(
            icon: const Icon(Icons.quiz),
            tooltip: 'Take Quiz',
            onPressed: () => Navigator.pushNamed(context, '/quiz', arguments: content),
          ),
          IconButton(
            icon: const Icon(Icons.school),
            tooltip: 'Ask AI Tutor',
            onPressed: () => Navigator.pushNamed(context, '/tutor', arguments: content),
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'Video History',
            onPressed: () => Navigator.pushNamed(context, '/history'),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Video Player ──────────────────────────────────
            if (videoUrl != null)
              EduVideoPlayer(videoUrl: videoUrl, title: title),

            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Stats Row ─────────────────────────────────
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _chip(Icons.movie, '${sceneList.length} Scenes', const Color(0xFF6C63FF)),
                      if (video != null)
                        _chip(Icons.timer, '${video['duration']}s', const Color(0xFF4ECDC4)),
                      if (subtitle != null)
                        _chip(Icons.subtitles, '${subtitle['total_entries']} subs', const Color(0xFFFFE66D)),
                      if (video != null)
                        _chip(Icons.speed, '${video['render_time_s'] ?? 0}s render', const Color(0xFFFF6B6B)),
                      _modeBadge(mode),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // ── Download & Share ──────────────────────────
                  if (video != null) ...[
                    const Text('🚀 Share & Download',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: downloadUrl == null
                                ? null
                                : () {
                                    // Web: open URL in new tab = download
                                    Clipboard.setData(ClipboardData(text: downloadUrl));
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('📥 Video URL copied — paste in browser to download:\n$downloadUrl'),
                                        duration: const Duration(seconds: 4),
                                        backgroundColor: const Color(0xFF6C63FF),
                                      ),
                                    );
                                  },
                            icon: const Icon(Icons.download),
                            label: const Text('Download'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF6C63FF),
                              padding: const EdgeInsets.symmetric(vertical: 14),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: _isSharing
                                ? null
                                : () => _createShareLink(video, title),
                            icon: _isSharing
                                ? const SizedBox(
                                    width: 16, height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                : const Icon(Icons.share),
                            label: Text(_shareUrl != null ? 'Link Copied!' : 'Share'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF4ECDC4),
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (_shareUrl != null) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF4ECDC4).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF4ECDC4).withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.link, size: 14, color: Color(0xFF4ECDC4)),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _shareUrl!,
                                style: const TextStyle(color: Color(0xFF4ECDC4), fontSize: 12),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.copy, size: 16, color: Color(0xFF4ECDC4)),
                              padding: EdgeInsets.zero,
                              onPressed: () => Clipboard.setData(ClipboardData(text: _shareUrl!)),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                  ],

                  // ── Performance Feedback ──────────────────────
                  _buildModeFeedbackCard(mode),
                  const SizedBox(height: 24),

                  // ── Summary ───────────────────────────────────
                  if (scenes['summary'] != null) ...[
                    const Text('📋 Summary',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1A1F38),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF6C63FF).withOpacity(0.3)),
                      ),
                      child: Text(scenes['summary'],
                          style: const TextStyle(color: Colors.white70, height: 1.5)),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // ── Scenes ────────────────────────────────────
                  const Text('🎬 Scenes',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  ...sceneList.map((scene) => _buildSceneCard(scene)),
                  const SizedBox(height: 24),

                  // ── Action Buttons ────────────────────────────
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () =>
                              Navigator.pushNamed(context, '/quiz', arguments: content),
                          icon: const Icon(Icons.quiz),
                          label: const Text('Take Quiz'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF4ECDC4),
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () =>
                              Navigator.pushNamed(context, '/tutor', arguments: content),
                          icon: const Icon(Icons.school),
                          label: const Text('Ask Tutor'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF6C63FF),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(IconData icon, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _modeBadge(String mode) {
    final modeInfo = {
      'basic':    {'icon': '🌱', 'color': const Color(0xFF4CAF50)},
      'beginner': {'icon': '📘', 'color': const Color(0xFF2196F3)},
      'advanced': {'icon': '🔥', 'color': const Color(0xFFFF5722)},
    };
    final info = modeInfo[mode] ?? modeInfo['beginner']!;
    final color = info['color'] as Color;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        '${info['icon']} ${mode[0].toUpperCase()}${mode.substring(1)} Mode',
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildModeFeedbackCard(String mode) {
    final feedbacks = {
      'basic': {
        'title': '🌱 Basic Mode Complete!',
        'message': 'Great start! You\'ve watched the simplified overview. Ready to go deeper?',
        'tip': 'Try Beginner mode next to unlock more detailed explanations.',
        'color': const Color(0xFF4CAF50),
        'next': 'beginner',
      },
      'beginner': {
        'title': '📘 Beginner Mode Complete!',
        'message': 'Well done! You\'ve covered the key concepts. Challenge yourself further!',
        'tip': 'Try Advanced mode for expert-level technical depth.',
        'color': const Color(0xFF2196F3),
        'next': 'advanced',
      },
      'advanced': {
        'title': '🔥 Advanced Mode Complete!',
        'message': 'Excellent! You\'ve tackled the full technical depth of this topic.',
        'tip': 'Take the quiz to test your mastery, then explore related topics.',
        'color': const Color(0xFFFF5722),
        'next': null,
      },
    };
    final fb = feedbacks[mode] ?? feedbacks['beginner']!;
    final color = fb['color'] as Color;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.15), color.withOpacity(0.05)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(fb['title'] as String,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
          const SizedBox(height: 8),
          Text(fb['message'] as String,
              style: const TextStyle(color: Colors.white70, height: 1.4)),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.lightbulb_outline, size: 14, color: color),
              const SizedBox(width: 6),
              Expanded(
                child: Text(fb['tip'] as String,
                    style: TextStyle(color: color, fontSize: 12, fontStyle: FontStyle.italic)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSceneCard(Map<String, dynamic> scene) {
    const emotionEmoji = {
      'neutral': '📝', 'curious': '🔍', 'excited': '⚡',
      'serious': '📌', 'calm': '🌿', 'surprised': '💡', 'joy': '😊',
    };
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 16,
                  backgroundColor: const Color(0xFF6C63FF),
                  child: Text('${scene['scene_id'] ?? '?'}',
                      style: const TextStyle(color: Colors.white, fontSize: 13)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(scene['title'] ?? 'Scene',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                ),
                Text(emotionEmoji[scene['emotion']] ?? '📝',
                    style: const TextStyle(fontSize: 20)),
              ],
            ),
            const SizedBox(height: 10),
            Text(scene['narration'] ?? '',
                style: const TextStyle(color: Colors.white60, height: 1.4),
                maxLines: 3, overflow: TextOverflow.ellipsis),
            if (scene['key_concepts'] != null) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                children: (scene['key_concepts'] as List)
                    .map<Widget>((c) => Chip(
                          label: Text(c, style: const TextStyle(fontSize: 11)),
                          backgroundColor: const Color(0xFF6C63FF).withOpacity(0.2),
                          padding: EdgeInsets.zero,
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
