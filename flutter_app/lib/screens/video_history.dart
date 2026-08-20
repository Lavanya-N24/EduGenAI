import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';

class VideoHistoryScreen extends StatefulWidget {
  const VideoHistoryScreen({super.key});

  @override
  State<VideoHistoryScreen> createState() => _VideoHistoryScreenState();
}

class _VideoHistoryScreenState extends State<VideoHistoryScreen> {
  List<Map<String, dynamic>> _videos = [];
  bool _loading = true;
  String? _error;

  static const String _userId = 'default_user';

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await ApiService.getUserVideos(_userId);
      setState(() {
        _videos = List<Map<String, dynamic>>.from(data['videos'] ?? []);
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _shareVideo(Map<String, dynamic> video) async {
    if (video['share_token'] != null) {
      final url = '${ApiService.baseUrl}/api/share/${video['share_token']}';
      await Clipboard.setData(ClipboardData(text: url));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('🔗 Share link copied!'), backgroundColor: Color(0xFF4ECDC4)),
        );
      }
      return;
    }
    try {
      final result = await ApiService.createShareLink(
        userId: _userId,
        filename: video['filename'],
        title: video['title'] ?? 'EduGenAI Video',
        duration: (video['duration'] ?? 0).toDouble(),
      );
      final url = result['share_url'] ?? '';
      await Clipboard.setData(ClipboardData(text: url));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('🔗 Share link copied!\n$url'),
              backgroundColor: const Color(0xFF4ECDC4), duration: const Duration(seconds: 4)),
        );
      }
      _loadHistory();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Share failed: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('📁 My Videos'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadHistory),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: Colors.white54)),
                    const SizedBox(height: 16),
                    ElevatedButton(onPressed: _loadHistory, child: const Text('Retry')),
                  ]))
              : _videos.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.video_library_outlined, size: 64, color: Colors.white24),
                          const SizedBox(height: 16),
                          const Text('No videos yet', style: TextStyle(color: Colors.white38, fontSize: 16)),
                          const SizedBox(height: 8),
                          const Text('Generate your first video from the home screen.',
                              style: TextStyle(color: Colors.white24, fontSize: 13)),
                          const SizedBox(height: 24),
                          ElevatedButton.icon(
                            onPressed: () => Navigator.pushReplacementNamed(context, '/'),
                            icon: const Icon(Icons.add),
                            label: const Text('Create Video'),
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6C63FF)),
                          ),
                        ],
                      ))
                  : RefreshIndicator(
                      onRefresh: _loadHistory,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _videos.length,
                        itemBuilder: (context, i) => _buildVideoCard(_videos[i]),
                      ),
                    ),
    );
  }

  Widget _buildVideoCard(Map<String, dynamic> video) {
    final modeColors = {
      'basic':    const Color(0xFF4CAF50),
      'beginner': const Color(0xFF2196F3),
      'advanced': const Color(0xFFFF5722),
    };
    final modeIcons = {'basic': '🌱', 'beginner': '📘', 'advanced': '🔥'};
    final mode = video['learning_mode'] ?? 'beginner';
    final modeColor = modeColors[mode] ?? const Color(0xFF2196F3);
    final exists = video['exists'] == true;
    final hasShare = video['share_token'] != null;
    final createdAt = video['created_at'] != null
        ? DateTime.tryParse(video['created_at'])
        : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title row
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF6C63FF).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.movie, color: Color(0xFF6C63FF), size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(video['title'] ?? 'Untitled Video',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                          maxLines: 1, overflow: TextOverflow.ellipsis),
                      if (createdAt != null)
                        Text(
                          '${createdAt.day}/${createdAt.month}/${createdAt.year}  ${createdAt.hour}:${createdAt.minute.toString().padLeft(2, '0')}',
                          style: const TextStyle(color: Colors.white38, fontSize: 11),
                        ),
                    ],
                  ),
                ),
                // Mode badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: modeColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: modeColor.withOpacity(0.4)),
                  ),
                  child: Text('${modeIcons[mode]} $mode',
                      style: TextStyle(color: modeColor, fontSize: 11, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Stats chips
            Wrap(
              spacing: 8, runSpacing: 6,
              children: [
                _statChip(Icons.timer_outlined, '${video['duration'] ?? 0}s', Colors.white54),
                _statChip(Icons.movie_outlined, '${video['scenes'] ?? 0} scenes', Colors.white54),
                _statChip(Icons.language, video['language'] ?? 'en', Colors.white54),
                if (video['render_time'] != null && video['render_time'] > 0)
                  _statChip(Icons.speed, '${video['render_time']}s render', const Color(0xFF4ECDC4)),
                if (!exists)
                  _statChip(Icons.error_outline, 'File missing', Colors.redAccent),
              ],
            ),
            const SizedBox(height: 14),

            // Action buttons
            Row(
              children: [
                // Download
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: exists ? () {
                      final url = '${ApiService.baseUrl}${video['video_url']}';
                      Clipboard.setData(ClipboardData(text: url));
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('📥 Copied download URL:\n$url'),
                          backgroundColor: const Color(0xFF6C63FF),
                          duration: const Duration(seconds: 4),
                        ),
                      );
                    } : null,
                    icon: const Icon(Icons.download, size: 16),
                    label: const Text('Download', style: TextStyle(fontSize: 13)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF6C63FF),
                      side: const BorderSide(color: Color(0xFF6C63FF)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                // Share
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: exists ? () => _shareVideo(video) : null,
                    icon: Icon(hasShare ? Icons.link : Icons.share, size: 16),
                    label: Text(hasShare ? 'Copy Link' : 'Share',
                        style: const TextStyle(fontSize: 13)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF4ECDC4),
                      side: const BorderSide(color: Color(0xFF4ECDC4)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _statChip(IconData icon, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(label, style: TextStyle(color: color, fontSize: 11)),
        ],
      ),
    );
  }
}
