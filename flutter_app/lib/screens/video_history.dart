import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import '../main.dart' show AppColors;
import '../services/api_service.dart';
import '../services/auth_service.dart';

class VideoHistoryScreen extends StatefulWidget {
  const VideoHistoryScreen({super.key});

  @override
  State<VideoHistoryScreen> createState() => _VideoHistoryScreenState();
}

class _VideoHistoryScreenState extends State<VideoHistoryScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _serverVideos = [];

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    final user = AuthService.instance.currentUser;
    final userId = user?.id ?? 'default_user';

    try {
      final videos = await ApiService.getUserVideoHistory(userId);
      if (mounted) {
        setState(() {
          _serverVideos = videos;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _showItemOptions(
    BuildContext context,
    String docId,
    String title,
    bool isPinned,
    Map<String, dynamic> fullData,
  ) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        margin: const EdgeInsets.all(16),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF222222) : Colors.white,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(
                isPinned ? Icons.push_pin_outlined : Icons.push_pin_rounded,
                size: 20,
                color: const Color(0xFFD97706),
              ),
              title: Text(isPinned ? 'Unpin item' : 'Pin item to top'),
              onTap: () async {
                Navigator.pop(ctx);
                await AuthService.instance.togglePinHistoryItem(docId, isPinned);
                setState(() {});
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline, color: Colors.redAccent, size: 20),
              title: const Text('Delete from History', style: TextStyle(color: Colors.redAccent)),
              onTap: () async {
                Navigator.pop(ctx);
                await AuthService.instance.deleteHistoryItem(docId);
                _serverVideos.removeWhere((v) => v['filename'] == docId || v['title'] == title);
                setState(() {});
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : const Color(0xFFFAF9F5);
    final user = AuthService.instance.currentUser;
    final userName = user?.name ?? 'Learner';
    final userInitial = userName.isNotEmpty ? userName[0].toUpperCase() : 'L';

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: isDark ? Colors.white : AppColors.ink),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'History & Saved Lessons',
          style: TextStyle(
            fontFamily: 'Georgia',
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: isDark ? Colors.white : AppColors.ink,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh History',
            onPressed: _loadHistory,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: Color(0xFFD97706)))
                  : StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                      stream: AuthService.instance.getUserHistoryStream(),
                      builder: (context, snapshot) {
                        final firestoreDocs = snapshot.data?.docs ?? [];
                        final localItems = AuthService.instance.getLocalHistory();

                        final allItems = <Map<String, dynamic>>[];

                        // 1. Add server videos
                        for (final vid in _serverVideos) {
                          final filename = vid['filename']?.toString() ?? '';
                          final title = vid['title']?.toString() ?? 'Generated Lesson';
                          final duration = vid['duration'] ?? 0;
                          final videoUrl = 'http://127.0.0.1:8000/videos/$filename';

                          allItems.add({
                            'id': filename,
                            'title': title,
                            'mode': 'Video Lesson (${duration > 0 ? "${duration.toInt()}s" : "HD"})',
                            'isPinned': false,
                            'data': {
                              'topic': title,
                              'title': title,
                              'video_url': videoUrl,
                              'video': {
                                'filename': filename,
                                'url': videoUrl,
                              },
                            },
                          });
                        }

                        // 2. Add Firestore items
                        for (final doc in firestoreDocs) {
                          final data = doc.data();
                          final exists = allItems.any((e) => e['title'] == data['title']);
                          if (!exists) {
                            allItems.add({
                              'id': doc.id,
                              'title': data['title'] ?? 'Untitled Lesson',
                              'mode': data['mode'] ?? 'beginner',
                              'isPinned': data['isPinned'] ?? false,
                              'data': data['data'] ?? {'topic': data['title']},
                            });
                          }
                        }

                        // 3. Add local items
                        for (final local in localItems) {
                          final exists = allItems.any((e) => e['title'] == local['title']);
                          if (!exists) {
                            allItems.add(local);
                          }
                        }

                        if (allItems.isEmpty) {
                          return Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.history_edu_outlined, size: 54, color: Colors.grey.shade400),
                                const SizedBox(height: 14),
                                Text(
                                  'No generated history yet',
                                  style: TextStyle(
                                    color: isDark ? Colors.white70 : AppColors.ink,
                                    fontFamily: 'Georgia',
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Generate your first video lesson from Home!',
                                  style: TextStyle(
                                    color: isDark ? Colors.white54 : AppColors.inkSoft,
                                    fontFamily: 'Roboto',
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }

                        final pinned = allItems.where((d) => (d['isPinned'] ?? false) == true).toList();
                        final recents = allItems.where((d) => (d['isPinned'] ?? false) == false).toList();

                        return RefreshIndicator(
                          color: const Color(0xFFD97706),
                          onRefresh: _loadHistory,
                          child: ListView(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            children: [
                              if (pinned.isNotEmpty) ...[
                                Row(
                                  children: [
                                    const Icon(Icons.push_pin_rounded, size: 14, color: Color(0xFFD97706)),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Pinned',
                                      style: TextStyle(
                                        fontFamily: 'Roboto',
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                ...pinned.map((item) => _buildHistoryRow(context, item, isDark, isPinned: true)),
                                const SizedBox(height: 16),
                              ],
                              if (recents.isNotEmpty) ...[
                                Row(
                                  children: [
                                    const Icon(Icons.access_time_rounded, size: 14, color: Colors.grey),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Generated Video Lessons (${recents.length})',
                                      style: TextStyle(
                                        fontFamily: 'Roboto',
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                ...recents.map((item) => _buildHistoryRow(context, item, isDark, isPinned: false)),
                              ],
                            ],
                          ),
                        );
                      },
                    ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: isDark ? const Color(0x1FFFFFFF) : AppColors.border)),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 16,
                    backgroundColor: const Color(0xFFD946EF),
                    child: Text(
                      userInitial,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          userName,
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          'EduGen Pro',
                          style: TextStyle(
                            fontSize: 11,
                            color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Icon(Icons.settings_outlined, size: 20, color: isDark ? Colors.white70 : AppColors.inkSoft),
                    onPressed: () => Navigator.pushNamed(context, '/theme-selector'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryRow(
    BuildContext context,
    Map<String, dynamic> item,
    bool isDark, {
    required bool isPinned,
  }) {
    final docId = item['id']?.toString() ?? 'item_${DateTime.now().millisecondsSinceEpoch}';
    final title = item['title']?.toString() ?? 'Untitled Lesson';
    final mode = (item['mode']?.toString() ?? 'VIDEO').toUpperCase();
    final payload = (item['data'] is Map<String, dynamic>)
        ? item['data'] as Map<String, dynamic>
        : {'topic': title, 'title': title};

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF222222) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: isDark ? const Color(0x1FFFFFFF) : AppColors.border),
      ),
      child: ListTile(
        dense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        leading: Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isPinned
                ? const Color(0xFFD97706).withValues(alpha: 0.15)
                : (isDark ? Colors.white10 : const Color(0xFFF3EFE6)),
          ),
          child: Icon(
            isPinned ? Icons.push_pin_rounded : Icons.play_circle_fill_rounded,
            size: 20,
            color: isPinned ? const Color(0xFFD97706) : const Color(0xFFD97706),
          ),
        ),
        title: Text(
          title,
          style: TextStyle(
            fontFamily: 'Roboto',
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: isDark ? Colors.white : AppColors.ink,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          mode,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.bold,
            color: Color(0xFFD97706),
          ),
        ),
        trailing: IconButton(
          icon: Icon(Icons.more_vert_rounded, size: 18, color: isDark ? Colors.white54 : AppColors.inkSoft),
          onPressed: () => _showItemOptions(context, docId, title, isPinned, payload),
        ),
        onTap: () {
          Navigator.pushNamed(context, '/result', arguments: payload);
        },
      ),
    );
  }
}