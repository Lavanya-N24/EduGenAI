import 'package:flutter/material.dart';
import '../main.dart' show AppColors;
import '../services/api_service.dart';
import '../services/auth_service.dart';

class QuizScreen extends StatefulWidget {
  final Map<String, dynamic>? initialData;
  const QuizScreen({super.key, this.initialData});

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  final TextEditingController _topicController = TextEditingController();
  final TextEditingController _contentController = TextEditingController();

  String _topic = 'Photosynthesis';
  String _difficulty = 'medium';
  int _questionCount = 5;

  bool _isConfiguring = true;
  bool _isLoading = false;
  List<Map<String, dynamic>> _questions = [];
  int _currentIndex = 0;
  int? _selectedOptionIndex;
  bool _isAnswerSubmitted = false;
  int _score = 0;
  bool _quizCompleted = false;
  final List<Map<String, dynamic>> _recordedAnswers = [];
  Map<String, dynamic>? _submissionResult;

  final List<String> _suggestedTopics = [
    'Photosynthesis',
    'Quantum Physics',
    'Machine Learning',
    'Cell Structure',
    'World History',
    'Newton\'s Laws',
  ];

  @override
  void initState() {
    super.initState();
    _topicController.text = 'Photosynthesis';
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_questions.isEmpty && _isConfiguring) {
      final args = ModalRoute.of(context)?.settings.arguments;
      if (args is Map<String, dynamic>) {
        final passedTopic = args['topic'] ?? args['title'] ?? '';
        final passedContent = args['summary'] ?? args['content'] ?? args['wiki_extract'] ?? '';

        if (passedTopic.isNotEmpty) {
          _topic = passedTopic;
          _topicController.text = passedTopic;
          _contentController.text = passedContent;
        }

        if (args['quiz'] is List && (args['quiz'] as List).isNotEmpty) {
          _loadQuestionsFromList(args['quiz'] as List);
          _isConfiguring = false;
          return;
        } else if (args['quiz'] is Map &&
            args['quiz']['questions'] is List &&
            (args['quiz']['questions'] as List).isNotEmpty) {
          _loadQuestionsFromList(args['quiz']['questions'] as List);
          _isConfiguring = false;
          return;
        }

        if (passedTopic.isNotEmpty) {
          // If came from a lesson with a topic, automatically start generation
          _isConfiguring = false;
          _startQuizGeneration();
        }
      }
    }
  }

  @override
  void dispose() {
    _topicController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  void _loadQuestionsFromList(List rawList) {
    final normalized = <Map<String, dynamic>>[];
    for (int i = 0; i < rawList.length; i++) {
      final item = rawList[i];
      if (item is Map) {
        final options = List<String>.from((item['options'] as List? ?? []).map((e) => e.toString()));
        int correctIdx = 0;
        final rawCorrect = item['correct_answer'] ?? item['correctAnswer'];

        if (rawCorrect is int) {
          correctIdx = rawCorrect.clamp(0, options.isNotEmpty ? options.length - 1 : 0);
        } else if (rawCorrect is String) {
          final s = rawCorrect.trim().toUpperCase();
          if (s.startsWith('A') || s == '0') {
            correctIdx = 0;
          } else if (s.startsWith('B') || s == '1') {
            correctIdx = 1;
          } else if (s.startsWith('C') || s == '2') {
            correctIdx = 2;
          } else if (s.startsWith('D') || s == '3') {
            correctIdx = 3;
          }
        }

        normalized.add({
          'id': item['id'] ?? (i + 1),
          'question': item['question'] ?? 'Question ${i + 1}',
          'options': options.isNotEmpty ? options : ['Option A', 'Option B', 'Option C', 'Option D'],
          'correctAnswer': correctIdx,
          'correct_answer': String.fromCharCode(65 + correctIdx),
          'explanation': item['explanation'] ?? 'Review the lesson concepts for more details.',
          'difficulty': item['difficulty'] ?? _difficulty,
          'concept_tested': item['concept_tested'] ?? 'Core Knowledge',
        });
      }
    }

    if (normalized.isNotEmpty) {
      setState(() {
        _questions = normalized;
        _isConfiguring = false;
        _isLoading = false;
        _currentIndex = 0;
        _score = 0;
        _selectedOptionIndex = null;
        _isAnswerSubmitted = false;
        _quizCompleted = false;
        _recordedAnswers.clear();
      });
    }
  }

  Future<void> _startQuizGeneration() async {
    final topic = _topicController.text.trim();
    final content = _contentController.text.trim();

    if (topic.isEmpty && content.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a topic or paste lesson content')),
      );
      return;
    }

    setState(() {
      _topic = topic.isNotEmpty ? topic : 'Core Concepts';
      _isConfiguring = false;
      _isLoading = true;
    });

    try {
      final response = await ApiService.generateQuiz(
        topic: _topic,
        content: content.isNotEmpty ? content : _topic,
        count: _questionCount,
        difficulty: _difficulty,
      );

      if (response['questions'] != null && (response['questions'] as List).isNotEmpty) {
        _loadQuestionsFromList(response['questions'] as List);
      } else {
        _loadFallbackQuiz();
      }
    } catch (_) {
      _loadFallbackQuiz();
    }
  }

  void _loadFallbackQuiz() {
    setState(() {
      _questions = [
        {
          'id': 1,
          'question': 'What is the primary mechanism involved in $_topic?',
          'options': [
            'System input energy transformation and synthesis',
            'Arbitrary random static storage',
            'Isolated assumptions without verified data',
            'None of the above'
          ],
          'correctAnswer': 0,
          'correct_answer': 'A',
          'explanation': 'Understanding the core mechanisms is essential for mastering $_topic.'
        },
        {
          'id': 2,
          'question': 'Which component plays a foundational role in this subject?',
          'options': [
            'Core structural inputs and energy conversion',
            'External arbitrary constants',
            'Unrelated historical blocks',
            'Isolated components'
          ],
          'correctAnswer': 0,
          'correct_answer': 'A',
          'explanation': 'Input processes and energy conversion form the basis of the framework.'
        },
        {
          'id': 3,
          'question': 'How can you best apply the principles learned in this lesson?',
          'options': [
            'Through continuous practice, analysis, and active testing',
            'By ignoring experimental observations',
            'Restricting study to memorization only',
            'None of the above'
          ],
          'correctAnswer': 0,
          'correct_answer': 'A',
          'explanation': 'Active problem solving solidifies the conceptual knowledge of $_topic.'
        }
      ];
      _isLoading = false;
    });
  }

  void _submitAnswer() {
    if (_selectedOptionIndex == null) return;

    final q = _questions[_currentIndex];
    final int correctIdx = q['correctAnswer'] is int ? q['correctAnswer'] as int : 0;
    final isCorrect = _selectedOptionIndex == correctIdx;

    setState(() {
      _isAnswerSubmitted = true;
      if (isCorrect) {
        _score++;
      }
      _recordedAnswers.add({
        'question': q['question'],
        'selected': String.fromCharCode(65 + (_selectedOptionIndex ?? 0)),
        'correct': String.fromCharCode(65 + correctIdx),
        'is_correct': isCorrect,
      });
    });
  }

  void _nextQuestion() async {
    if (_currentIndex < _questions.length - 1) {
      setState(() {
        _currentIndex++;
        _selectedOptionIndex = null;
        _isAnswerSubmitted = false;
      });
    } else {
      // Quiz complete - Submit results to backend for adaptive learning
      final user = AuthService.instance.currentUser;
      final userId = user?.id ?? 'default_user';

      try {
        final res = await ApiService.submitQuiz(
          userId: userId,
          topic: _topic,
          difficulty: _difficulty,
          answers: _recordedAnswers,
        );
        _submissionResult = res['result'];
      } catch (_) {}

      setState(() {
        _quizCompleted = true;
      });
    }
  }

  void _restartQuiz() {
    setState(() {
      _currentIndex = 0;
      _selectedOptionIndex = null;
      _isAnswerSubmitted = false;
      _score = 0;
      _quizCompleted = false;
      _recordedAnswers.clear();
      _submissionResult = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : AppColors.cream;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        title: Text(
          _isConfiguring
              ? 'Quiz Arena • Generate Quiz'
              : 'Knowledge Check: $_topic',
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (!_isConfiguring && _questions.isNotEmpty && !_quizCompleted) {
              setState(() => _isConfiguring = true);
            } else {
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          if (!_isConfiguring)
            IconButton(
              icon: const Icon(Icons.tune_rounded),
              tooltip: 'New Topic / Settings',
              onPressed: () => setState(() => _isConfiguring = true),
            ),
        ],
      ),
      body: SafeArea(
        child: _isConfiguring
            ? _buildConfigurationView(isDark)
            : _isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const CircularProgressIndicator(color: Color(0xFFD97706)),
                        const SizedBox(height: 18),
                        Text(
                          'Generating ${_difficulty.toUpperCase()} quiz on "$_topic"...',
                          style: TextStyle(
                            fontFamily: 'Georgia',
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Crafting multiple choice questions & explanations',
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 13,
                            color: isDark ? Colors.white60 : AppColors.inkSoft,
                          ),
                        ),
                      ],
                    ),
                  )
                : _quizCompleted
                    ? _buildScoreSummary(isDark)
                    : _buildQuizBody(isDark),
      ),
    );
  }

  // ── 1. QUIZ CONFIGURATION & TOPIC INPUT VIEW ──
  Widget _buildConfigurationView(bool isDark) {
    final cardColor = isDark ? const Color(0xFF222222) : Colors.white;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: cardColor,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFFD97706).withValues(alpha: 0.15),
                      ),
                      child: const Icon(Icons.psychology_rounded, size: 28, color: Color(0xFFD97706)),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Custom AI Quiz Generator',
                            style: TextStyle(
                              fontFamily: 'Georgia',
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : AppColors.ink,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Generate smart, adaptive MCQs from any subject, question, or study material.',
                            style: TextStyle(
                              fontFamily: 'Roboto',
                              fontSize: 13,
                              color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Topic Input Section
              Text(
                '1. What topic would you like to be quizzed on?',
                style: TextStyle(
                  fontFamily: 'Roboto',
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : AppColors.ink,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: cardColor,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: isDark ? const Color(0x1FFFFFFF) : AppColors.border),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: TextField(
                  controller: _topicController,
                  style: TextStyle(color: isDark ? Colors.white : AppColors.ink, fontSize: 15),
                  decoration: const InputDecoration(
                    hintText: 'e.g. Photosynthesis, Binary Search Trees, World War II',
                    border: InputBorder.none,
                  ),
                ),
              ),

              const SizedBox(height: 12),

              // Quick Topic Suggestions
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _suggestedTopics.map((topic) {
                  final isSelected = _topicController.text == topic;
                  return ActionChip(
                    label: Text(topic, style: const TextStyle(fontSize: 12)),
                    backgroundColor: isSelected
                        ? const Color(0xFFD97706).withValues(alpha: 0.2)
                        : (isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF3EFE6)),
                    side: BorderSide(
                      color: isSelected ? const Color(0xFFD97706) : Colors.transparent,
                    ),
                    onPressed: () {
                      setState(() {
                        _topicController.text = topic;
                      });
                    },
                  );
                }).toList(),
              ),

              const SizedBox(height: 24),

              // Optional Content Context
              Text(
                '2. Optional: Paste notes / source text (RAG context)',
                style: TextStyle(
                  fontFamily: 'Roboto',
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : AppColors.ink,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: cardColor,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: isDark ? const Color(0x1FFFFFFF) : AppColors.border),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: TextField(
                  controller: _contentController,
                  maxLines: 3,
                  style: TextStyle(color: isDark ? Colors.white : AppColors.ink, fontSize: 14),
                  decoration: const InputDecoration(
                    hintText: 'Paste any lecture notes, article excerpts, or book paragraphs here...',
                    border: InputBorder.none,
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // Difficulty & Question Count Selectors
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Difficulty
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Difficulty Level',
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: ['easy', 'medium', 'hard'].map((lvl) {
                            final isSel = _difficulty == lvl;
                            return Expanded(
                              child: Padding(
                                padding: const EdgeInsets.only(right: 6),
                                child: InkWell(
                                  onTap: () => setState(() => _difficulty = lvl),
                                  borderRadius: BorderRadius.circular(12),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(vertical: 10),
                                    decoration: BoxDecoration(
                                      color: isSel
                                          ? const Color(0xFFD97706)
                                          : (isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF3EFE6)),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Center(
                                      child: Text(
                                        lvl[0].toUpperCase() + lvl.substring(1),
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                          color: isSel ? Colors.white : (isDark ? Colors.white70 : AppColors.ink),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(width: 16),

                  // Question Count
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Questions Count',
                          style: TextStyle(
                            fontFamily: 'Roboto',
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: isDark ? Colors.white : AppColors.ink,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [3, 5, 10].map((count) {
                            final isSel = _questionCount == count;
                            return Expanded(
                              child: Padding(
                                padding: const EdgeInsets.only(right: 6),
                                child: InkWell(
                                  onTap: () => setState(() => _questionCount = count),
                                  borderRadius: BorderRadius.circular(12),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(vertical: 10),
                                    decoration: BoxDecoration(
                                      color: isSel
                                          ? const Color(0xFFD97706)
                                          : (isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF3EFE6)),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Center(
                                      child: Text(
                                        '$count Qs',
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold,
                                          color: isSel ? Colors.white : (isDark ? Colors.white70 : AppColors.ink),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // Generate Quiz Action Button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: _startQuizGeneration,
                  icon: const Icon(Icons.bolt_rounded, size: 22),
                  label: const Text(
                    'Generate Smart Quiz ✨',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFD97706),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── 2. ACTIVE QUIZ QUESTIONS VIEW ──
  Widget _buildQuizBody(bool isDark) {
    final cardColor = isDark ? const Color(0xFF222222) : Colors.white;
    final q = _questions[_currentIndex];
    final options = List<String>.from(q['options'] ?? []);
    final int correctIdx = q['correctAnswer'] is int ? q['correctAnswer'] as int : 0;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Progress Indicator
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Question ${_currentIndex + 1} of ${_questions.length}',
                    style: TextStyle(
                      fontFamily: 'Roboto',
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFD97706).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'Score: $_score',
                      style: const TextStyle(
                        color: Color(0xFFD97706),
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: (_currentIndex + 1) / _questions.length,
                  backgroundColor: isDark ? Colors.white12 : AppColors.border,
                  color: const Color(0xFFD97706),
                  minHeight: 6,
                ),
              ),
              const SizedBox(height: 24),

              // Question Card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: cardColor,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                  ),
                ),
                child: Text(
                  q['question'] ?? 'Question',
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: isDark ? Colors.white : AppColors.ink,
                    height: 1.4,
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Options List
              ...List.generate(options.length, (index) {
                final isSelected = _selectedOptionIndex == index;
                Color borderColor = isDark ? const Color(0x1FFFFFFF) : AppColors.border;
                Color optionBg = cardColor;

                if (_isAnswerSubmitted) {
                  if (index == correctIdx) {
                    borderColor = const Color(0xFF10B981);
                    optionBg = const Color(0xFF10B981).withValues(alpha: 0.12);
                  } else if (isSelected && index != correctIdx) {
                    borderColor = AppColors.error;
                    optionBg = AppColors.error.withValues(alpha: 0.12);
                  }
                } else if (isSelected) {
                  borderColor = const Color(0xFFD97706);
                  optionBg = const Color(0xFFD97706).withValues(alpha: 0.08);
                }

                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: _isAnswerSubmitted
                        ? null
                        : () => setState(() => _selectedOptionIndex = index),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                      decoration: BoxDecoration(
                        color: optionBg,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: borderColor, width: isSelected ? 2 : 1),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 28,
                            height: 28,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isSelected
                                  ? const Color(0xFFD97706)
                                  : (isDark ? Colors.white10 : const Color(0xFFF3EFE6)),
                            ),
                            child: Center(
                              child: Text(
                                String.fromCharCode(65 + index),
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: isSelected ? Colors.white : (isDark ? Colors.white70 : AppColors.ink),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Text(
                              options[index],
                              style: TextStyle(
                                fontFamily: 'Roboto',
                                fontSize: 15,
                                color: isDark ? Colors.white : AppColors.ink,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),

              // Explanation Box (Shown after submitting)
              if (_isAnswerSubmitted && q['explanation'] != null)
                Container(
                  margin: const EdgeInsets.only(top: 8, bottom: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF64748B).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.info_outline, size: 20, color: Color(0xFF3B82F6)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          q['explanation'],
                          style: TextStyle(
                            fontSize: 13,
                            color: isDark ? Colors.white70 : const Color(0xFF334155),
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 16),

              // Bottom Action Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _selectedOptionIndex == null
                      ? null
                      : _isAnswerSubmitted
                          ? _nextQuestion
                          : _submitAnswer,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFD97706),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(26),
                    ),
                  ),
                  child: Text(
                    !_isAnswerSubmitted
                        ? 'Check Answer'
                        : _currentIndex < _questions.length - 1
                            ? 'Next Question →'
                            : 'Finish & Submit 🎉',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── 3. SCORE SUMMARY VIEW ──
  Widget _buildScoreSummary(bool isDark) {
    final double percentage = _questions.isNotEmpty ? (_score / _questions.length) * 100 : 0;
    final cardColor = isDark ? const Color(0xFF222222) : Colors.white;

    final feedback = _submissionResult?['feedback'];
    final feedbackMsg = feedback is Map ? feedback['message'] : null;
    final feedbackRec = feedback is Map ? feedback['recommendation'] : null;
    final nextDiff = _submissionResult?['new_difficulty'] ?? _difficulty;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Container(
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: cardColor,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: (percentage >= 70 ? const Color(0xFF10B981) : const Color(0xFFD97706))
                      .withValues(alpha: 0.15),
                ),
                child: Icon(
                  percentage >= 70 ? Icons.emoji_events_rounded : Icons.psychology_rounded,
                  size: 48,
                  color: percentage >= 70 ? const Color(0xFF10B981) : const Color(0xFFD97706),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                percentage >= 80
                    ? '🌟 Mastery Achieved!'
                    : percentage >= 50
                        ? '👍 Great Effort!'
                        : '📚 Needs More Practice',
                style: const TextStyle(
                  fontFamily: 'Georgia',
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'You scored $_score / ${_questions.length} (${percentage.toInt()}%) on "$_topic"',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: percentage >= 70 ? const Color(0xFF10B981) : const Color(0xFFD97706),
                ),
              ),
              const SizedBox(height: 14),
              if (feedbackMsg != null)
                Text(
                  feedbackMsg,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: isDark ? Colors.white70 : AppColors.ink,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              if (feedbackRec != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    feedbackRec,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: isDark ? Colors.white54 : AppColors.inkSoft,
                      fontSize: 13,
                    ),
                  ),
                ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: isDark ? Colors.white10 : const Color(0xFFF3EFE6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'Adaptive Level: ${nextDiff.toString().toUpperCase()}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFFD97706),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _restartQuiz,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                      ),
                      child: const Text('Retake Quiz'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () => setState(() => _isConfiguring = true),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFD97706),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                      ),
                      child: const Text('New Quiz'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextButton.icon(
                onPressed: () {
                  Navigator.pushReplacementNamed(context, '/tutor', arguments: {
                    'topic': _topic,
                    'content': _contentController.text.isNotEmpty ? _contentController.text : _topic,
                  });
                },
                icon: const Icon(Icons.school_outlined, size: 18),
                label: const Text('Discuss with AI Tutor →'),
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFFD97706),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}