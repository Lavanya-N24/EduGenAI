import 'package:flutter/material.dart';
import '../main.dart' show AppColors;
import '../services/api_service.dart';
import '../services/auth_service.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  bool _isLoading = true;
  Map<String, dynamic> _analytics = {};

  @override
  void initState() {
    super.initState();
    _loadAnalytics();
  }

  Future<void> _loadAnalytics() async {
    setState(() => _isLoading = true);
    final user = AuthService.instance.currentUser;
    final userId = user?.id ?? 'default_user';

    try {
      final data = await ApiService.getAnalytics(userId);
      if (mounted) {
        setState(() {
          _analytics = data;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : AppColors.cream;
    final cardColor = isDark ? const Color(0xFF222222) : Colors.white;

    final double accuracy = (_analytics['overall_accuracy'] as num?)?.toDouble() ?? 0.0;
    final int totalQuizzes = (_analytics['total_quizzes'] as num?)?.toInt() ?? 0;
    final int totalQuestions = (_analytics['total_questions_answered'] as num?)?.toInt() ?? 0;
    final String difficulty = (_analytics['current_difficulty']?.toString() ?? 'Medium').toUpperCase();
    final String trendDir = _analytics['trend_direction']?.toString() ?? 'steady';
    final List weakAreas = _analytics['weak_areas'] is List ? _analytics['weak_areas'] : [];
    final List strongAreas = _analytics['strong_areas'] is List ? _analytics['strong_areas'] : [];
    final Map<String, dynamic> topicBreakdown = _analytics['topic_breakdown'] is Map
        ? Map<String, dynamic>.from(_analytics['topic_breakdown'])
        : {};
    final List recentSessions = _analytics['recent_sessions'] is List
        ? List.from(_analytics['recent_sessions'])
        : [];

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        title: const Text('Learning Analytics & Mastery'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
            onPressed: _loadAnalytics,
          ),
        ],
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: Color(0xFFD97706)))
            : RefreshIndicator(
                color: const Color(0xFFD97706),
                onRefresh: _loadAnalytics,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Top KPI Row
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricCard(
                              label: totalQuestions > 0 ? 'Quizzes ($totalQuestions Qs)' : 'Quizzes Taken',
                              value: '$totalQuizzes',
                              icon: Icons.assignment_turned_in_outlined,
                              color: const Color(0xFFD97706),
                              cardColor: cardColor,
                              isDark: isDark,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildMetricCard(
                              label: 'Overall Accuracy',
                              value: '${accuracy.toStringAsFixed(0)}%',
                              icon: Icons.emoji_events_outlined,
                              color: const Color(0xFF10B981),
                              cardColor: cardColor,
                              isDark: isDark,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: _buildMetricCard(
                              label: 'Current Level',
                              value: difficulty,
                              icon: Icons.trending_up_rounded,
                              color: const Color(0xFF3B82F6),
                              cardColor: cardColor,
                              isDark: isDark,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildMetricCard(
                              label: 'Performance Trend',
                              value: trendDir == 'improving' ? 'Improving 🚀' : 'Steady 📈',
                              icon: Icons.local_fire_department_outlined,
                              color: const Color(0xFFEF4444),
                              cardColor: cardColor,
                              isDark: isDark,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 28),

                      // Weak & Strong Areas
                      if (weakAreas.isNotEmpty || strongAreas.isNotEmpty) ...[
                        Text(
                          'Concept Focus Areas',
                          style: TextStyle(
                            fontFamily: 'Georgia',
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: cardColor,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (strongAreas.isNotEmpty) ...[
                                const Row(
                                  children: [
                                    Icon(Icons.check_circle_rounded, size: 16, color: Color(0xFF10B981)),
                                    SizedBox(width: 6),
                                    Text(
                                      'Mastered Concepts',
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  children: strongAreas.map((t) => Chip(
                                    label: Text(t.toString(), style: const TextStyle(fontSize: 12)),
                                    backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.12),
                                    side: const BorderSide(color: Color(0xFF10B981), width: 0.5),
                                  )).toList(),
                                ),
                                const SizedBox(height: 14),
                              ],
                              if (weakAreas.isNotEmpty) ...[
                                const Row(
                                  children: [
                                    Icon(Icons.info_outline, size: 16, color: Color(0xFFEF4444)),
                                    SizedBox(width: 6),
                                    Text(
                                      'Concepts Needing Review',
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  children: weakAreas.map((t) => ActionChip(
                                    label: Text(t.toString(), style: const TextStyle(fontSize: 12)),
                                    backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.12),
                                    side: const BorderSide(color: Color(0xFFEF4444), width: 0.5),
                                    onPressed: () {
                                      Navigator.pushNamed(context, '/tutor', arguments: {'topic': t.toString()});
                                    },
                                  )).toList(),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(height: 28),
                      ],

                      // Topic Mastery Breakdown
                      Text(
                        'Topic Performance Breakdown',
                        style: TextStyle(
                          fontFamily: 'Georgia',
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: isDark ? Colors.white : AppColors.ink,
                        ),
                      ),
                      const SizedBox(height: 14),

                      if (topicBreakdown.isEmpty)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: cardColor,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                            ),
                          ),
                          child: Column(
                            children: [
                              Icon(Icons.quiz_outlined, size: 40, color: Colors.grey.shade400),
                              const SizedBox(height: 10),
                              Text(
                                'No quiz data recorded yet',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  color: isDark ? Colors.white70 : AppColors.ink,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Take a quiz after generating any video lesson to track your learning progress!',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: isDark ? Colors.white54 : AppColors.inkSoft,
                                ),
                              ),
                              const SizedBox(height: 14),
                              ElevatedButton.icon(
                                onPressed: () => Navigator.pushNamed(context, '/quiz'),
                                icon: const Icon(Icons.play_arrow_rounded, size: 18),
                                label: const Text('Take a Practice Quiz'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFFD97706),
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: cardColor,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                            ),
                          ),
                          child: Column(
                            children: topicBreakdown.entries.map((entry) {
                              final topicName = entry.key;
                              final details = entry.value is Map ? entry.value as Map : {};
                              final avgScore = (details['average_score'] as num?)?.toDouble() ?? 0.0;
                              final attempts = details['attempts'] ?? 1;

                              final color = avgScore >= 80
                                  ? const Color(0xFF10B981)
                                  : avgScore >= 50
                                      ? const Color(0xFFF59E0B)
                                      : const Color(0xFFEF4444);

                              return Padding(
                                padding: const EdgeInsets.only(bottom: 16),
                                child: _buildProgressBar(
                                  topicName,
                                  avgScore / 100.0,
                                  '${avgScore.toStringAsFixed(0)}% ($attempts attempts)',
                                  color,
                                  isDark,
                                ),
                              );
                            }).toList(),
                          ),
                        ),

                      const SizedBox(height: 28),

                      // Recent Learning Sessions
                      if (recentSessions.isNotEmpty) ...[
                        Text(
                          'Recent Quiz Sessions',
                          style: TextStyle(
                            fontFamily: 'Georgia',
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 14),
                        ...recentSessions.reversed.take(5).map((session) {
                          final topic = session['topic'] ?? 'General Concept';
                          final score = (session['score'] as num?)?.toInt() ?? 0;
                          final correct = session['correct'] ?? 0;
                          final total = session['total'] ?? 0;
                          final diff = session['difficulty'] ?? 'medium';

                          return _buildActivityTile(
                            topic.toString(),
                            '${diff.toString().toUpperCase()} • Score: $score% ($correct/$total correct)',
                            score >= 70 ? 'Passed 🎉' : 'Needs Review',
                            score >= 70,
                            isDark,
                            cardColor,
                          );
                        }),
                      ],
                    ],
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildMetricCard({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
    required Color cardColor,
    required bool isDark,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.w700,
              fontFamily: 'Georgia',
              color: isDark ? Colors.white : AppColors.ink,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontFamily: 'Roboto',
              color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressBar(String title, double progress, String percent, Color color, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontFamily: 'Roboto',
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                  color: isDark ? Colors.white : AppColors.ink,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              percent,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 12,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            backgroundColor: isDark ? Colors.white10 : AppColors.border,
            color: color,
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildActivityTile(
    String title,
    String subtitle,
    String status,
    bool isPassed,
    bool isDark,
    Color cardColor,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: (isPassed ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isPassed ? Icons.check_circle_outline : Icons.replay_rounded,
              color: isPassed ? const Color(0xFF10B981) : const Color(0xFFEF4444),
              size: 18,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontFamily: 'Roboto',
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: isDark ? Colors.white : AppColors.ink,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                  ),
                ),
              ],
            ),
          ),
          Text(
            status,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: isPassed ? const Color(0xFF10B981) : const Color(0xFFEF4444),
            ),
          ),
        ],
      ),
    );
  }
}