import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'package:flutter_animate/flutter_animate.dart';

class QuizScreen extends StatefulWidget {
  const QuizScreen({super.key});

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> with TickerProviderStateMixin {
  Map<String, dynamic>? _quiz;
  bool _isLoading = false;
  bool _isSubmitted = false;
  Map<int, String> _selectedAnswers = {};
  Map<String, dynamic>? _result;
  String _content = '';
  int _currentQ = 0;

  late AnimationController _glowCtrl;

  @override
  void initState() {
    super.initState();
    _glowCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
  }

  @override
  void dispose() { _glowCtrl.dispose(); super.dispose(); }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final args = ModalRoute.of(context)?.settings.arguments;
    if (args is String && args.isNotEmpty && _quiz == null) {
      _content = args;
      _generateQuiz();
    }
  }

  Future<void> _generateQuiz() async {
    if (_content.isEmpty) return;
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.generateQuiz(content: _content);
      setState(() { _quiz = response['quiz'] ?? response; _isLoading = false; _currentQ = 0; });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) _snack('Error: $e', Colors.redAccent);
    }
  }

  Future<void> _submitQuiz() async {
    if (_quiz == null) return;
    final questions = (_quiz!['questions'] as List?) ?? [];
    final answers = questions.map<Map<String, dynamic>>((q) {
      int id = q['id'];
      return {'question_id': id, 'selected': _selectedAnswers[id] ?? '', 'correct': q['correct_answer']};
    }).toList();
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.submitQuiz(
          userId: 'default_user', topic: _quiz!['quiz_title'] ?? 'General', answers: answers);
      setState(() { _result = response['result'] ?? response; _isSubmitted = true; _isLoading = false; });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) _snack('Error: $e', Colors.redAccent);
    }
  }

  void _snack(String msg, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg), backgroundColor: color, behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF080C1A),
      appBar: _buildAppBar(),
      body: _isLoading ? _buildLoader() : _quiz == null ? _buildEmptyState() : _buildQuiz(),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    final questions = (_quiz?['questions'] as List?) ?? [];
    return AppBar(
      backgroundColor: const Color(0xFF080C1A),
      elevation: 0,
      leading: IconButton(
        icon: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: Colors.white.withAlpha(12), borderRadius: BorderRadius.circular(10)),
          child: const Icon(Icons.arrow_back_ios_new_rounded, size: 16, color: Colors.white),
        ),
        onPressed: () => Navigator.pop(context),
      ),
      title: ShaderMask(
        shaderCallback: (b) => const LinearGradient(
            colors: [Color(0xFFFFE66D), Color(0xFFFF6B6B)]).createShader(b),
        child: const Text('Quiz', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 20)),
      ),
      actions: [
        if (_quiz != null && !_isSubmitted && questions.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(child: Text('${_selectedAnswers.length}/${questions.length}',
                style: const TextStyle(color: Colors.white54, fontSize: 13))),
          ),
      ],
    );
  }

  Widget _buildLoader() {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        AnimatedBuilder(
          animation: _glowCtrl,
          builder: (_, __) => Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFFFFE66D).withAlpha(20),
              boxShadow: [BoxShadow(color: const Color(0xFFFFE66D).withAlpha((40 + _glowCtrl.value * 60).round()),
                  blurRadius: 40, spreadRadius: 5)],
            ),
            child: const CircularProgressIndicator(color: Color(0xFFFFE66D), strokeWidth: 3),
          ),
        ),
        const SizedBox(height: 20),
        const Text('Generating quiz with AI...', style: TextStyle(color: Colors.white54, fontSize: 14)),
        const SizedBox(height: 6),
        Text('Crafting personalized questions...', style: TextStyle(color: Colors.white.withAlpha(60), fontSize: 12)),
      ]),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [const Color(0xFFFFE66D).withAlpha(40), Colors.transparent]),
            ),
            child: const Icon(Icons.quiz_rounded, size: 72, color: Color(0xFFFFE66D)),
          ),
          const SizedBox(height: 20),
          const Text('Ready to Test Your Knowledge?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white),
              textAlign: TextAlign.center),
          const SizedBox(height: 10),
          Text('Generate a video first and tap "Take Quiz",\nor enter content manually below.',
              style: TextStyle(color: Colors.white.withAlpha(100), fontSize: 13), textAlign: TextAlign.center),
          const SizedBox(height: 28),
          GestureDetector(
            onTap: _showContentInput,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFFFFE66D), Color(0xFFFF6B6B)]),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [BoxShadow(color: const Color(0xFFFFE66D).withAlpha(100), blurRadius: 20)],
              ),
              child: const Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.edit_rounded, color: Colors.black, size: 18),
                SizedBox(width: 10),
                Text('Enter Content', style: TextStyle(color: Colors.black, fontWeight: FontWeight.w800, fontSize: 15)),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  void _showContentInput() {
    final ctrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: const Color(0xFF0E1226),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Enter Quiz Content', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.white)),
            const SizedBox(height: 16),
            TextField(
              controller: ctrl, maxLines: 5,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Paste educational content here...',
                hintStyle: TextStyle(color: Colors.white.withAlpha(50)),
                filled: true, fillColor: const Color(0xFF080C1A),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.all(14),
              ),
            ),
            const SizedBox(height: 20),
            Row(children: [
              Expanded(child: OutlinedButton(
                onPressed: () => Navigator.pop(ctx),
                style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.white24)),
                child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
              )),
              const SizedBox(width: 12),
              Expanded(child: GestureDetector(
                onTap: () {
                  Navigator.pop(ctx);
                  setState(() => _content = ctrl.text);
                  _generateQuiz();
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFFFFE66D), Color(0xFFFF6B6B)]),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Center(child: Text('Generate', style: TextStyle(
                      color: Colors.black, fontWeight: FontWeight.w800, fontSize: 14))),
                ),
              )),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _buildQuiz() {
    final questions = (_quiz!['questions'] as List?) ?? [];

    if (_isSubmitted && _result != null) {
      return _buildResultScreen(questions);
    }

    return Column(children: [
      // Progress bar
      _buildProgressBar(questions.length),
      Expanded(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // Quiz title
            ShaderMask(
              shaderCallback: (b) => const LinearGradient(
                  colors: [Colors.white, Color(0xFFBBBBBB)]).createShader(b),
              child: Text(_quiz!['quiz_title'] ?? 'Quiz',
                  style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
            ),
            const SizedBox(height: 6),
            Text('${questions.length} questions  •  Answer all to submit',
                style: TextStyle(color: Colors.white.withAlpha(100), fontSize: 12)),
            const SizedBox(height: 24),
            ...questions.asMap().entries.map((e) => _buildQuestionCard(e.key, e.value)),
          ]),
        ),
      ),
      // Submit button area
      _buildSubmitBar(questions),
    ]);
  }

  Widget _buildProgressBar(int total) {
    final progress = total == 0 ? 0.0 : _selectedAnswers.length / total;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      color: const Color(0xFF080C1A),
      child: Column(children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text('Progress', style: TextStyle(color: Colors.white.withAlpha(120), fontSize: 12)),
          Text('${_selectedAnswers.length}/$total answered',
              style: const TextStyle(color: Color(0xFFFFE66D), fontSize: 12, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: Colors.white.withAlpha(15),
            valueColor: const AlwaysStoppedAnimation(Color(0xFFFFE66D)),
            minHeight: 6,
          ),
        ),
      ]),
    );
  }

  Widget _buildSubmitBar(List questions) {
    final allAnswered = _selectedAnswers.length == questions.length && questions.isNotEmpty;
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      decoration: BoxDecoration(
        color: const Color(0xFF080C1A),
        border: Border(top: BorderSide(color: Colors.white.withAlpha(15))),
      ),
      child: SizedBox(
        width: double.infinity, height: 54,
        child: GestureDetector(
          onTap: allAnswered ? _submitQuiz : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            decoration: BoxDecoration(
              gradient: allAnswered
                  ? const LinearGradient(colors: [Color(0xFFFFE66D), Color(0xFFFF6B6B)])
                  : LinearGradient(colors: [Colors.white.withAlpha(15), Colors.white.withAlpha(8)]),
              borderRadius: BorderRadius.circular(14),
              boxShadow: allAnswered ? [BoxShadow(color: const Color(0xFFFFE66D).withAlpha(100), blurRadius: 20)] : [],
            ),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(Icons.check_circle_rounded, color: allAnswered ? Colors.black : Colors.white24, size: 20),
              const SizedBox(width: 10),
              Text('Submit Answers', style: TextStyle(
                  color: allAnswered ? Colors.black : Colors.white24,
                  fontSize: 16, fontWeight: FontWeight.w800)),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _buildResultScreen(List questions) {
    final score = (_result!['score'] as num?)?.toDouble() ?? 0;
    final isGood = score >= 70;
    final feedback = _result!['feedback'] as Map<String, dynamic>?;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(children: [
        // Score hero
        Container(
          width: double.infinity, padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isGood
                  ? [const Color(0xFF4ECDC4), const Color(0xFF6C63FF)]
                  : [const Color(0xFFFF6B6B), const Color(0xFFFF8E53)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [BoxShadow(
              color: (isGood ? const Color(0xFF4ECDC4) : const Color(0xFFFF6B6B)).withAlpha(100),
              blurRadius: 30, spreadRadius: 2, offset: const Offset(0, 8))],
          ),
          child: Column(children: [
            Text(isGood ? '🏆' : '💪', style: const TextStyle(fontSize: 48)),
            const SizedBox(height: 8),
            Text('${score.toStringAsFixed(0)}%',
                style: const TextStyle(color: Colors.white, fontSize: 64, fontWeight: FontWeight.w900, letterSpacing: -2)),
            Text(feedback?['message'] ?? (isGood ? 'Great job!' : 'Keep practicing!'),
                style: const TextStyle(color: Colors.white, fontSize: 16), textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(25), borderRadius: BorderRadius.circular(20)),
              child: Text('Next Level: ${_result!['new_difficulty'] ?? 'same'}',
                  style: const TextStyle(color: Colors.white, fontSize: 13)),
            ),
          ]),
        ).animate().scale(duration: 600.ms, curve: Curves.elasticOut),
        const SizedBox(height: 20),

        if (feedback?['recommendation'] != null)
          Container(
            width: double.infinity, padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(6), borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withAlpha(15)),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('💡 ', style: TextStyle(fontSize: 18)),
              Expanded(child: Text(feedback!['recommendation'],
                  style: TextStyle(color: Colors.white.withAlpha(180), fontSize: 14, height: 1.5))),
            ]),
          ),
        const SizedBox(height: 24),

        // Answers review
        ...questions.asMap().entries.map((e) => _buildReviewCard(e.key, e.value)),
        const SizedBox(height: 20),

        GestureDetector(
          onTap: () {
            setState(() { _quiz = null; _isSubmitted = false; _selectedAnswers = {}; _result = null; });
            _generateQuiz();
          },
          child: Container(
            width: double.infinity, height: 54,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFFFE66D), Color(0xFFFF6B6B)]),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: const Color(0xFFFFE66D).withAlpha(100), blurRadius: 20)],
            ),
            child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(Icons.refresh_rounded, color: Colors.black),
              SizedBox(width: 10),
              Text('Try Again', style: TextStyle(color: Colors.black, fontWeight: FontWeight.w800, fontSize: 16)),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _buildQuestionCard(int index, Map<String, dynamic> q) {
    int qId = q['id'];
    List options = q['options'] ?? [];
    String? correct = q['correct_answer'];
    bool answered = _selectedAnswers.containsKey(qId);

    final diffColors = {'easy': const Color(0xFF4CAF50), 'medium': const Color(0xFFFFE66D), 'hard': const Color(0xFFFF5722)};
    final diffColor = diffColors[q['difficulty']] ?? Colors.white38;

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1226),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: answered ? const Color(0xFF6C63FF).withAlpha(100) : Colors.white.withAlpha(15)),
        boxShadow: answered ? [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(40), blurRadius: 12)] : [],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const LinearGradient(colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)]),
            ),
            child: Center(child: Text('${index + 1}',
                style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800))),
          ),
          const SizedBox(width: 10),
          if (q['difficulty'] != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
              decoration: BoxDecoration(
                color: diffColor.withAlpha(25), borderRadius: BorderRadius.circular(8),
                border: Border.all(color: diffColor.withAlpha(80)),
              ),
              child: Text(q['difficulty'], style: TextStyle(color: diffColor, fontSize: 11, fontWeight: FontWeight.w600)),
            ),
          const Spacer(),
          if (answered)
            const Icon(Icons.check_circle_rounded, color: Color(0xFF6C63FF), size: 18),
        ]),
        const SizedBox(height: 14),
        Text(q['question'] ?? '',
            style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600, height: 1.4)),
        const SizedBox(height: 14),
        ...options.map<Widget>((option) {
          final letter = option.toString().substring(0, 1);
          final selected = _selectedAnswers[qId] == letter;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: GestureDetector(
              onTap: _isSubmitted ? null : () => setState(() => _selectedAnswers[qId] = letter),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: double.infinity, padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: selected ? const Color(0xFF6C63FF).withAlpha(40) : Colors.white.withAlpha(6),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: selected ? const Color(0xFF6C63FF) : Colors.white.withAlpha(20),
                    width: selected ? 1.5 : 1,
                  ),
                  boxShadow: selected ? [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(60), blurRadius: 10)] : [],
                ),
                child: Row(children: [
                  Container(
                    width: 24, height: 24,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: selected ? const Color(0xFF6C63FF) : Colors.white.withAlpha(15),
                    ),
                    child: Center(child: Text(letter,
                        style: TextStyle(color: selected ? Colors.white : Colors.white54,
                            fontSize: 12, fontWeight: FontWeight.w700))),
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Text(option.toString().length > 2 ? option.toString().substring(3) : option.toString(),
                      style: TextStyle(color: selected ? Colors.white : Colors.white70, fontSize: 14))),
                ]),
              ),
            ),
          );
        }),
      ]),
    ).animate().fadeIn(delay: (index * 80).ms, duration: 350.ms).slideY(begin: 0.08, end: 0);
  }

  Widget _buildReviewCard(int index, Map<String, dynamic> q) {
    int qId = q['id'];
    final selected = _selectedAnswers[qId] ?? '';
    final correct = q['correct_answer'] ?? '';
    final isCorrect = selected == correct;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isCorrect ? const Color(0xFF4CAF50).withAlpha(15) : Colors.redAccent.withAlpha(15),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isCorrect ? const Color(0xFF4CAF50).withAlpha(80) : Colors.redAccent.withAlpha(80)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(isCorrect ? Icons.check_circle_rounded : Icons.cancel_rounded,
              color: isCorrect ? const Color(0xFF4CAF50) : Colors.redAccent, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text('Q${index + 1}. ${q['question'] ?? ''}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13), maxLines: 2)),
        ]),
        if (!isCorrect && q['explanation'] != null) ...[
          const SizedBox(height: 10),
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(Icons.lightbulb_rounded, size: 14, color: Color(0xFFFFE66D)),
            const SizedBox(width: 8),
            Expanded(child: Text(q['explanation'],
                style: TextStyle(color: Colors.white.withAlpha(160), fontSize: 12, height: 1.4))),
          ]),
        ],
      ]),
    );
  }
}
