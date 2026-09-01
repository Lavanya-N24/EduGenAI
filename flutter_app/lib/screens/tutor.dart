import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../main.dart' show AppColors;
import '../services/api_service.dart';
import '../services/auth_service.dart';

class TutorScreen extends StatefulWidget {
  final Map<String, dynamic>? initialData;
  const TutorScreen({super.key, this.initialData});

  @override
  State<TutorScreen> createState() => _TutorScreenState();
}

class _TutorScreenState extends State<TutorScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<Map<String, String>> _messages = [];
  bool _isTyping = false;
  String _topicContext = 'General Studies';
  String _lessonContent = '';

  final List<String> _quickPrompts = [
    'Explain this like I am 10',
    'Give me a real-world example',
    'What are the key takeaways?',
    'Create a memory mnemonic',
  ];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_messages.isEmpty) {
      final args = ModalRoute.of(context)?.settings.arguments;
      if (args is Map<String, dynamic>) {
        _topicContext = args['topic'] ?? args['title'] ?? 'your topic';
        _lessonContent = args['summary'] ?? args['content'] ?? args['wiki_extract'] ?? '';
      }
      _messages.add({
        'role': 'assistant',
        'content':
            'Hello! I am EduBot, your dedicated AI Tutor. Ask me anything about "$_topicContext" or choose a prompt below to get started!',
      });
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage([String? presetText]) async {
    final text = presetText ?? _messageController.text.trim();
    if (text.isEmpty) return;

    if (presetText == null) _messageController.clear();

    setState(() {
      _messages.add({'role': 'user', 'content': text});
      _isTyping = true;
    });
    _scrollToBottom();

    try {
      final user = AuthService.instance.currentUser;
      final userId = user?.id ?? 'default_user';

      // Pass full multi-turn conversation history
      final response = await ApiService.askTutor(
        question: text,
        topicContext: _topicContext,
        contentContext: _lessonContent.isNotEmpty ? _lessonContent : _topicContext,
        chatHistory: _messages.sublist(0, _messages.length - 1),
        userId: userId,
      );

      final reply = response['reply'] ??
          response['response'] ??
          'Here is a breakdown to help you understand:\n\n$text connects directly to the core fundamentals of $_topicContext.';

      if (mounted) {
        setState(() {
          _messages.add({
            'role': 'assistant',
            'content': reply,
          });
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add({
            'role': 'assistant',
            'content':
                'I am your EduBot Tutor for $_topicContext. To understand "$text", focus on how the core components interact step-by-step.',
          });
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isTyping = false);
        _scrollToBottom();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF161616) : AppColors.cream;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'EduBot • AI Study Tutor',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            Text(
              _topicContext,
              style: TextStyle(
                fontSize: 12,
                color: isDark ? const Color(0xFFA0A6C0) : AppColors.inkSoft,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Clear Chat',
            onPressed: () {
              setState(() {
                _messages.clear();
                _messages.add({
                  'role': 'assistant',
                  'content': 'Chat reset. What would you like to explore about "$_topicContext"?',
                });
              });
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Chat Messages List
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                itemCount: _messages.length + (_isTyping ? 1 : 0),
                itemBuilder: (context, index) {
                  if (_isTyping && index == _messages.length) {
                    return _buildTypingIndicator(isDark);
                  }

                  final msg = _messages[index];
                  final isUser = msg['role'] == 'user';
                  return _buildMessageBubble(msg['content'] ?? '', isUser, isDark);
                },
              ),
            ),

            // Quick Prompts Chips
            if (!_isTyping)
              Container(
                height: 42,
                margin: const EdgeInsets.symmetric(vertical: 4),
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _quickPrompts.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final prompt = _quickPrompts[index];
                    return ActionChip(
                      label: Text(
                        prompt,
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? Colors.white70 : AppColors.ink,
                        ),
                      ),
                      backgroundColor: isDark ? const Color(0xFF222222) : Colors.white,
                      side: BorderSide(
                        color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                      onPressed: () => _sendMessage(prompt),
                    );
                  },
                ),
              ),

            // Input Bar
            Container(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                border: Border(
                  top: BorderSide(
                    color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF3EFE6),
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: TextField(
                        controller: _messageController,
                        style: TextStyle(color: isDark ? Colors.white : AppColors.ink),
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendMessage(),
                        decoration: InputDecoration(
                          hintText: 'Ask EduBot anything...',
                          hintStyle: TextStyle(
                            color: isDark ? Colors.white38 : AppColors.inkFaint,
                            fontSize: 14,
                          ),
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    decoration: const BoxDecoration(
                      color: Color(0xFFD97706),
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                      onPressed: _isTyping ? null : () => _sendMessage(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageBubble(String text, bool isUser, bool isDark) {
    const userBg = Color(0xFFD97706);
    final assistantBg = isDark ? const Color(0xFF222222) : Colors.white;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: const Color(0xFFD97706).withValues(alpha: 0.15),
              child: const Icon(Icons.school_rounded, size: 18, color: Color(0xFFD97706)),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: isUser ? userBg : assistantBg,
                borderRadius: BorderRadius.circular(18).copyWith(
                  bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(18),
                  bottomLeft: !isUser ? const Radius.circular(4) : const Radius.circular(18),
                ),
                border: isUser
                    ? null
                    : Border.all(
                        color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
                      ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SelectableText(
                    text,
                    style: TextStyle(
                      fontFamily: 'Roboto',
                      fontSize: 14,
                      height: 1.4,
                      color: isUser
                          ? Colors.white
                          : (isDark ? Colors.white : AppColors.ink),
                    ),
                  ),
                  if (!isUser) ...[
                    const SizedBox(height: 6),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        InkWell(
                          onTap: () {
                            Clipboard.setData(ClipboardData(text: text));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Copied response to clipboard')),
                            );
                          },
                          child: Row(
                            children: [
                              Icon(
                                Icons.copy_rounded,
                                size: 13,
                                color: isDark ? Colors.white38 : AppColors.inkFaint,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Copy',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: isDark ? Colors.white38 : AppColors.inkFaint,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              backgroundColor: isDark ? const Color(0xFF2C2C2C) : const Color(0xFFE5E7EB),
              child: Icon(
                Icons.person_rounded,
                size: 18,
                color: isDark ? Colors.white70 : AppColors.ink,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTypingIndicator(bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: const Color(0xFFD97706).withValues(alpha: 0.15),
            child: const Icon(Icons.school_rounded, size: 18, color: Color(0xFFD97706)),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF222222) : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark ? const Color(0x1FFFFFFF) : AppColors.border,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Color(0xFFD97706),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'EduBot is thinking...',
                  style: TextStyle(
                    fontSize: 13,
                    fontStyle: FontStyle.italic,
                    color: isDark ? Colors.white60 : AppColors.inkSoft,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}