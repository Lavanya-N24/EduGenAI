import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen>
    with SingleTickerProviderStateMixin {
  Map<String, dynamic>? _analytics;
  bool _isLoading = true;
  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
    _loadAnalytics();
  }

  @override
  void dispose() { _pulseCtrl.dispose(); super.dispose(); }

  Future<void> _loadAnalytics() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.getAnalytics('default_user');
      setState(() { _analytics = response['analytics'] ?? response; _isLoading = false; });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C1A),
      appBar: _buildAppBar(),
      body: _isLoading
          ? _buildLoader()
          : (_analytics == null || _analytics!['has_data'] == false)
              ? _buildEmptyState()
              : _buildDashboard(),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF080C1A),
      elevation: 0,
      leading: IconButton(
        icon: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withAlpha(12),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.arrow_back_ios_new_rounded, size: 16, color: Colors.white),
        ),
        onPressed: () => Navigator.pop(context),
      ),
      title: ShaderMask(
        shaderCallback: (b) => const LinearGradient(
            colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)]).createShader(b),
        child: const Text('Learning Analytics',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 20)),
      ),
      actions: [
        IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(12), borderRadius: BorderRadius.circular(10)),
            child: const Icon(Icons.refresh_rounded, size: 18, color: Colors.white),
          ),
          onPressed: _loadAnalytics,
        ),
        const SizedBox(width: 8),
      ],
    );
  }

  Widget _buildLoader() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        AnimatedBuilder(
          animation: _pulseCtrl,
          builder: (_, __) => Transform.scale(
            scale: 1.0 + _pulseCtrl.value * 0.1,
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF6C63FF).withAlpha(30),
                boxShadow: [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(60),
                    blurRadius: 30, spreadRadius: 5)],
              ),
              child: const CircularProgressIndicator(
                  color: Color(0xFF6C63FF), strokeWidth: 3),
            ),
          ),
        ),
        const SizedBox(height: 20),
        const Text('Loading your analytics...', style: TextStyle(color: Colors.white54, fontSize: 14)),
      ]),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [
              const Color(0xFF6C63FF).withAlpha(40), Colors.transparent]),
          ),
          child: const Icon(Icons.analytics_outlined, size: 72, color: Color(0xFF6C63FF)),
        ),
        const SizedBox(height: 20),
        const Text('No Data Yet', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colors.white)),
        const SizedBox(height: 8),
        Text('Take a quiz to start tracking\nyour learning progress!',
            style: TextStyle(color: Colors.white.withAlpha(100), fontSize: 14),
            textAlign: TextAlign.center),
        const SizedBox(height: 28),
        _gradientButton('Start Learning', Icons.play_arrow_rounded,
            () => Navigator.pushNamed(context, '/')),
      ]),
    );
  }

  Widget _buildDashboard() {
    final accuracy    = (_analytics!['overall_accuracy'] as num?)?.toDouble() ?? 0.0;
    final totalQuizzes = _analytics!['total_quizzes'] ?? 0;
    final difficulty  = _analytics!['current_difficulty'] ?? 'medium';
    final weakAreas   = (_analytics!['weak_areas'] as List?) ?? [];
    final strongAreas = (_analytics!['strong_areas'] as List?) ?? [];
    final trend       = (_analytics!['performance_trend'] as List?) ?? [];
    final topicBreak  = (_analytics!['topic_breakdown'] as Map<String, dynamic>?) ?? {};
    final trendDir    = _analytics!['trend_direction'] ?? 'stable';

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // ── Hero Score Card ───────────────────────────────
        _buildScoreHero(accuracy, totalQuizzes, difficulty),
        const SizedBox(height: 20),

        // ── Stats Row ─────────────────────────────────────
        Row(children: [
          _statCard('🎯', 'Quizzes', '$totalQuizzes', const Color(0xFF6C63FF)),
          const SizedBox(width: 12),
          _statCard('📊', 'Level', difficulty.toUpperCase(), const Color(0xFF4ECDC4)),
          const SizedBox(width: 12),
          _statCard('📈', 'Trend',
              trendDir == 'improving' ? '↗ UP' : '→ Stable',
              trendDir == 'improving' ? const Color(0xFF4CAF50) : const Color(0xFFFFE66D)),
        ]),
        const SizedBox(height: 28),

        // ── Trend Chart ───────────────────────────────────
        if (trend.isNotEmpty) ...[
          _sectionTitle('📈  Performance Trend'),
          const SizedBox(height: 12),
          _buildTrendChart(trend),
          const SizedBox(height: 28),
        ],

        // ── Weak Areas ────────────────────────────────────
        if (weakAreas.isNotEmpty) ...[
          _sectionTitle('⚠️  Needs Practice'),
          const SizedBox(height: 12),
          ...weakAreas.map((a) => _areaChip(a.toString(), Colors.redAccent, Icons.warning_amber_rounded)),
          const SizedBox(height: 28),
        ],

        // ── Strong Areas ──────────────────────────────────
        if (strongAreas.isNotEmpty) ...[
          _sectionTitle('⭐  Strong Areas'),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8,
              children: strongAreas.map((a) => _areaChip(a.toString(), const Color(0xFF4CAF50), Icons.star_rounded)).toList()),
          const SizedBox(height: 28),
        ],

        // ── Topic Breakdown ───────────────────────────────
        if (topicBreak.isNotEmpty) ...[
          _sectionTitle('📚  Topic Breakdown'),
          const SizedBox(height: 12),
          ...topicBreak.entries.map((e) => _topicCard(e.key, e.value)),
        ],
      ]),
    );
  }

  Widget _buildScoreHero(double accuracy, int quizzes, String difficulty) {
    final isGood = accuracy >= 70;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isGood
              ? [const Color(0xFF6C63FF), const Color(0xFF4ECDC4)]
              : [const Color(0xFFFF5722), const Color(0xFFFF8E53)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [BoxShadow(
          color: (isGood ? const Color(0xFF6C63FF) : const Color(0xFFFF5722)).withAlpha(100),
          blurRadius: 30, spreadRadius: 2, offset: const Offset(0, 8))],
      ),
      child: Column(children: [
        Text(isGood ? '🏆 Excellent Progress!' : '💪 Keep Practicing!',
            style: TextStyle(color: Colors.white.withAlpha(210), fontSize: 14)),
        const SizedBox(height: 12),
        Text('${accuracy.toStringAsFixed(1)}%',
            style: const TextStyle(color: Colors.white, fontSize: 58,
                fontWeight: FontWeight.w900, letterSpacing: -2)),
        const Text('Overall Accuracy',
            style: TextStyle(color: Colors.white70, fontSize: 14)),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.white.withAlpha(25), borderRadius: BorderRadius.circular(20)),
          child: Text('$quizzes quizzes  •  Level: $difficulty',
              style: const TextStyle(color: Colors.white, fontSize: 13)),
        ),
      ]),
    );
  }

  Widget _buildTrendChart(List trend) {
    return _glassPanel(
      child: SizedBox(
        height: 130,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: trend.asMap().entries.map((e) {
            final score = (e.value as num).toDouble();
            final isGood = score >= 70;
            return Column(mainAxisAlignment: MainAxisAlignment.end, children: [
              Text('${score.toInt()}%',
                  style: const TextStyle(fontSize: 10, color: Colors.white54)),
              const SizedBox(height: 4),
              Container(
                width: 32, height: (score * 0.8).clamp(8, 96),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isGood
                        ? [const Color(0xFF4ECDC4), const Color(0xFF6C63FF)]
                        : [const Color(0xFFFF6B6B), const Color(0xFFFF8E53)],
                    begin: Alignment.bottomCenter, end: Alignment.topCenter,
                  ),
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [BoxShadow(
                    color: (isGood ? const Color(0xFF4ECDC4) : const Color(0xFFFF6B6B)).withAlpha(80),
                    blurRadius: 8)],
                ),
              ),
              const SizedBox(height: 6),
              Text('Q${e.key + 1}', style: const TextStyle(fontSize: 10, color: Colors.white38)),
            ]);
          }).toList(),
        ),
      ),
    );
  }

  Widget _topicCard(String topic, dynamic details) {
    final d = details as Map<String, dynamic>;
    final score = (d['average_score'] as num?)?.toDouble() ?? 0;
    final attempts = d['attempts'] ?? 0;
    final isStrong = score >= 70;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1226),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withAlpha(15)),
      ),
      child: Row(children: [
        Container(
          width: 50, height: 50,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: isStrong
                  ? [const Color(0xFF4ECDC4), const Color(0xFF6C63FF)]
                  : [const Color(0xFFFF6B6B), const Color(0xFFFF8E53)],
            ),
          ),
          child: Center(child: Text('${score.toInt()}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14))),
        ),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(topic, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: Colors.white)),
          const SizedBox(height: 2),
          Text('$attempts attempts  •  ${d['difficulty'] ?? ''}',
              style: TextStyle(color: Colors.white.withAlpha(100), fontSize: 12)),
        ])),
        Icon(isStrong ? Icons.check_circle_rounded : Icons.error_rounded,
            color: isStrong ? const Color(0xFF4CAF50) : Colors.redAccent, size: 22),
      ]),
    );
  }

  Widget _areaChip(String label, Color color, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8), width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: color.withAlpha(20), borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Row(children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 12),
        Text(label, style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  Widget _statCard(String emoji, String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withAlpha(20), borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withAlpha(50)),
        ),
        child: Column(children: [
          Text(emoji, style: const TextStyle(fontSize: 22)),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(color: color, fontSize: 15, fontWeight: FontWeight.w800)),
          Text(label, style: TextStyle(color: color.withAlpha(180), fontSize: 10)),
        ]),
      ),
    );
  }

  Widget _sectionTitle(String t) => Text(t,
      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Colors.white));

  Widget _glassPanel({required Widget child}) {
    return Container(
      width: double.infinity, padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(6), borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withAlpha(15)),
      ),
      child: child,
    );
  }

  Widget _gradientButton(String label, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)]),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(100), blurRadius: 20)],
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, color: Colors.white, size: 20),
          const SizedBox(width: 10),
          Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15)),
        ]),
      ),
    );
  }
}
