import 'dart:math' as math;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with TickerProviderStateMixin {
  final _textCtrl = TextEditingController();
  String _lang = 'en';
  String _mode = 'beginner';
  Uint8List? _fileBytes;
  String? _fileName;
  bool _loading = false;
  String _status = '';

  late AnimationController _bgCtrl;
  late AnimationController _pulseCtrl;
  Animation<double>? _bgAnim;
  Animation<double>? _pulseAnim;

  static const _userId = 'default_user';

  final _langs = const {
    'en':'🇬🇧 English','hi':'🇮🇳 Hindi','ta':'🇮🇳 Tamil','te':'🇮🇳 Telugu',
    'ml':'🇮🇳 Malayalam','kn':'🇮🇳 Kannada','bn':'🇮🇳 Bengali','mr':'🇮🇳 Marathi',
    'fr':'🇫🇷 French','es':'🇪🇸 Spanish','de':'🇩🇪 German','ja':'🇯🇵 Japanese',
    'zh-cn':'🇨🇳 Chinese','ar':'🇸🇦 Arabic','ko':'🇰🇷 Korean','ru':'🇷🇺 Russian',
  };

  @override
  void initState() {
    super.initState();
    _bgCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 4))..repeat(reverse: true);
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
    _bgAnim = Tween<double>(begin: 0, end: 1).animate(CurvedAnimation(parent: _bgCtrl, curve: Curves.easeInOut));
    _pulseAnim = Tween<double>(begin: 1.0, end: 1.04).animate(CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _textCtrl.dispose(); _bgCtrl.dispose(); _pulseCtrl.dispose(); super.dispose(); }

  Future<void> _pickFile() async {
    final r = await FilePicker.platform.pickFiles(
      type: FileType.custom, withData: true,
      allowedExtensions: ['pdf','txt','png','jpg','jpeg','docx','pptx']);
    if (r?.files.single.bytes != null) {
      setState(() { _fileBytes = r!.files.single.bytes; _fileName = r.files.single.name; });
    }
  }

  Future<void> _generate() async {
    final hasText = _textCtrl.text.trim().isNotEmpty;
    if (!hasText && _fileBytes == null) { _snack('Enter text or upload a file'); return; }
    setState(() { _loading = true; _status = '🧠 AI is crafting your video...'; });
    try {
      final result = await ApiService.generateFullPipeline(
        text: hasText ? _textCtrl.text.trim() : null,
        fileBytes: _fileBytes, fileName: _fileName,
        targetLanguage: _lang, generateVideo: true,
        learningMode: _mode, userId: _userId,
      );
      if (mounted) Navigator.pushNamed(context, '/result', arguments: result);
    } catch (e) {
      if (mounted) _snack('Error: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(m), backgroundColor: Colors.redAccent,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF06080F),
      body: Stack(children: [
        _buildAnimatedBg(),
        SafeArea(child: SingleChildScrollView(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _buildHeroBanner(),
            _buildNavRow(),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const SizedBox(height: 28),
                _buildModeSelector(),
                const SizedBox(height: 28),
                _buildNeonDivider('📝  Your Content'),
                const SizedBox(height: 14),
                _buildTextInput(),
                const SizedBox(height: 14),
                _buildUploadTile(),
                const SizedBox(height: 28),
                _buildNeonDivider('🌐  Output Language'),
                const SizedBox(height: 14),
                _buildLanguagePicker(),
                const SizedBox(height: 36),
                _buildGenerateCTA(),
                const SizedBox(height: 40),
              ]),
            ),
          ]),
        )),
      ]),
    );
  }

  // ── Animated mesh background ──────────────────────────────
  Widget _buildAnimatedBg() {
    if (_bgAnim == null) return const SizedBox.shrink();
    return AnimatedBuilder(animation: _bgAnim!, builder: (_, __) {
      return CustomPaint(painter: _BgPainter(_bgAnim!.value), child: const SizedBox.expand());
    });
  }

  // ── Hero banner ───────────────────────────────────────────
  Widget _buildHeroBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 32),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [const Color(0xFF1A1040), const Color(0xFF0D1B2A), const Color(0xFF06080F)],
        ),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Logo pill
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)]),
            borderRadius: BorderRadius.circular(30),
            boxShadow: [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(120), blurRadius: 18, spreadRadius: 1)],
          ),
          child: const Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.auto_awesome, color: Colors.white, size: 16),
            SizedBox(width: 7),
            Text('EduGenAI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 1)),
          ]),
        ),
        const SizedBox(height: 20),
        // Big headline
        ShaderMask(
          shaderCallback: (b) => const LinearGradient(
            colors: [Colors.white, Color(0xFFB8B5FF)],
            begin: Alignment.topLeft, end: Alignment.bottomRight,
          ).createShader(b),
          child: const Text('Turn Any Content\nInto a Video Lesson',
            style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900, height: 1.2, letterSpacing: -0.5)),
        ),
        const SizedBox(height: 12),
        Text('AI-powered • Multi-language • Under 10 seconds',
          style: TextStyle(color: Colors.white.withAlpha(130), fontSize: 13, letterSpacing: 0.2)),
        const SizedBox(height: 20),
        // Stats row
        Row(children: [
          _heroBadge('⚡', '< 10s', 'Generation'),
          const SizedBox(width: 10),
          _heroBadge('🌐', '16+', 'Languages'),
          const SizedBox(width: 10),
          _heroBadge('🎯', '3', 'Levels'),
        ]),
      ]),
    );
  }

  Widget _heroBadge(String emoji, String val, String label) {
    return Expanded(child: Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(8),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withAlpha(20)),
      ),
      child: Column(children: [
        Text(emoji, style: const TextStyle(fontSize: 18)),
        const SizedBox(height: 4),
        Text(val, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
        Text(label, style: TextStyle(color: Colors.white.withAlpha(100), fontSize: 10)),
      ]),
    ));
  }

  // ── Nav row ───────────────────────────────────────────────
  Widget _buildNavRow() {
    final items = [
      ('Analytics', Icons.analytics_rounded, const Color(0xFF4ECDC4), '/analytics'),
      ('AI Tutor', Icons.school_rounded, const Color(0xFFFF6B6B), '/tutor'),
      ('Quiz', Icons.quiz_rounded, const Color(0xFFFFE66D), '/quiz'),
      ('History', Icons.video_library_rounded, const Color(0xFF6C63FF), '/history'),
    ];
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(6),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withAlpha(12)),
      ),
      child: Row(children: items.map((item) {
        final (label, icon, color, route) = item;
        return Expanded(child: GestureDetector(
          onTap: () => Navigator.pushNamed(context, route),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(13)),
            child: Column(children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(height: 4),
              Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w700)),
            ]),
          ),
        ));
      }).toList()),
    );
  }

  // ── Mode selector ─────────────────────────────────────────
  Widget _buildModeSelector() {
    final modes = [
      ('basic', '🌱', 'Basic', const Color(0xFF4CAF50)),
      ('beginner', '📘', 'Beginner', const Color(0xFF6C63FF)),
      ('advanced', '🔥', 'Advanced', const Color(0xFFFF5722)),
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _label('🎯  Learning Mode'),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(6),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Colors.white.withAlpha(12)),
        ),
        child: Row(children: modes.map((m) {
          final (id, emoji, name, color) = m;
          final sel = _mode == id;
          return Expanded(child: GestureDetector(
            onTap: () => setState(() => _mode = id),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOut,
              margin: const EdgeInsets.all(2),
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                gradient: sel ? LinearGradient(colors: [color.withAlpha(60), color.withAlpha(30)]) : null,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: sel ? color : Colors.transparent, width: 1.5),
                boxShadow: sel ? [BoxShadow(color: color.withAlpha(100), blurRadius: 14, spreadRadius: 0)] : [],
              ),
              child: Column(children: [
                AnimatedScale(scale: sel ? 1.15 : 1.0, duration: const Duration(milliseconds: 220),
                  child: Text(emoji, style: const TextStyle(fontSize: 22))),
                const SizedBox(height: 5),
                Text(name, style: TextStyle(
                  color: sel ? color : Colors.white54,
                  fontWeight: FontWeight.w800, fontSize: 12)),
              ]),
            ),
          ));
        }).toList()),
      ),
    ]);
  }

  // ── Neon divider ──────────────────────────────────────────
  Widget _buildNeonDivider(String title) {
    return Row(children: [
      Container(width: 3, height: 18, decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)], begin: Alignment.topCenter, end: Alignment.bottomCenter),
        borderRadius: BorderRadius.circular(3),
        boxShadow: [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(120), blurRadius: 8)],
      )),
      const SizedBox(width: 10),
      Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15, letterSpacing: 0.2)),
    ]);
  }

  // ── Text input ────────────────────────────────────────────
  Widget _buildTextInput() {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF6C63FF).withAlpha(70)),
        boxShadow: [BoxShadow(color: const Color(0xFF6C63FF).withAlpha(15), blurRadius: 20, spreadRadius: 2)],
      ),
      child: TextField(
        controller: _textCtrl, maxLines: 6,
        style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.6),
        decoration: InputDecoration(
          hintText: 'Paste topic or educational content here...\n\ne.g. "Explain photosynthesis for students"',
          hintStyle: TextStyle(color: Colors.white.withAlpha(35), fontSize: 13),
          filled: true, fillColor: const Color(0xFF0C1020),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
          contentPadding: const EdgeInsets.all(18),
        ),
      ),
    );
  }

  // ── Upload tile ───────────────────────────────────────────
  Widget _buildUploadTile() {
    final hasFile = _fileName != null;
    final color = hasFile ? const Color(0xFF4ECDC4) : const Color(0xFF6C63FF);
    return GestureDetector(
      onTap: _pickFile,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          color: color.withAlpha(16),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withAlpha(80)),
          boxShadow: [BoxShadow(color: color.withAlpha(20), blurRadius: 12)],
        ),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [color.withAlpha(160), color.withAlpha(80)]),
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: color.withAlpha(80), blurRadius: 10)],
            ),
            child: Icon(hasFile ? Icons.check_circle_rounded : Icons.cloud_upload_rounded,
                color: Colors.white, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(hasFile ? _fileName! : 'Upload a Document',
              style: TextStyle(color: hasFile ? color : Colors.white,
                  fontWeight: FontWeight.w700, fontSize: 14),
              maxLines: 1, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 2),
            Text(hasFile ? '${(_fileBytes!.length / 1024).toStringAsFixed(1)} KB  •  Tap to change'
                : 'PDF, DOCX, PPTX, TXT, Images',
              style: TextStyle(color: color.withAlpha(hasFile ? 180 : 120), fontSize: 11)),
          ])),
          if (hasFile)
            GestureDetector(
              onTap: () => setState(() { _fileBytes = null; _fileName = null; }),
              child: Icon(Icons.close_rounded, color: Colors.white.withAlpha(80), size: 18))
          else
            Icon(Icons.chevron_right_rounded, color: color.withAlpha(150), size: 22),
        ]),
      ),
    );
  }

  // ── Language picker ───────────────────────────────────────
  Widget _buildLanguagePicker() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      decoration: BoxDecoration(
        color: const Color(0xFF0C1020),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withAlpha(18)),
      ),
      child: DropdownButton<String>(
        value: _lang, isExpanded: true,
        dropdownColor: const Color(0xFF111827),
        underline: const SizedBox(),
        icon: const Icon(Icons.expand_more_rounded, color: Color(0xFF6C63FF)),
        style: const TextStyle(color: Colors.white, fontSize: 14),
        items: _langs.entries.map((e) =>
          DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
        onChanged: (v) => setState(() => _lang = v!),
      ),
    );
  }

  // ── Generate CTA ──────────────────────────────────────────
  Widget _buildGenerateCTA() {
    if (_loading || _pulseAnim == null) {
      return Container(
        height: 60, width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(8),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFF6C63FF).withAlpha(60)),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          SizedBox(width: 20, height: 20,
            child: CircularProgressIndicator(strokeWidth: 2,
                valueColor: const AlwaysStoppedAnimation(Color(0xFF6C63FF)))),
          const SizedBox(width: 14),
          Text(_status, style: const TextStyle(color: Colors.white60, fontSize: 14)),
        ]),
      );
    }
    return AnimatedBuilder(
      animation: _pulseAnim!,
      builder: (_, __) => Transform.scale(
        scale: _pulseAnim!.value,
        child: GestureDetector(
          onTap: _generate,
          child: Container(
            height: 62, width: double.infinity,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C63FF), Color(0xFF4361EE), Color(0xFF4ECDC4)],
                begin: Alignment.centerLeft, end: Alignment.centerRight,
              ),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(color: const Color(0xFF6C63FF).withAlpha(140),
                    blurRadius: 28, spreadRadius: 2, offset: const Offset(0, 6)),
                BoxShadow(color: const Color(0xFF4ECDC4).withAlpha(60),
                    blurRadius: 14, spreadRadius: 0, offset: const Offset(0, 2)),
              ],
            ),
            child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(Icons.movie_creation_rounded, color: Colors.white, size: 24),
              SizedBox(width: 12),
              Text('Generate Video', style: TextStyle(
                  color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: 0.4)),
              SizedBox(width: 10),
              Icon(Icons.rocket_launch_rounded, color: Colors.white70, size: 16),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _label(String t) => Text(t, style: const TextStyle(
      color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15, letterSpacing: 0.2));
}

// ── Mesh / Aurora background painter ─────────────────────────
class _BgPainter extends CustomPainter {
  final double t;
  _BgPainter(this.t);

  @override
  void paint(Canvas canvas, Size size) {
    void drawOrb(double x, double y, double r, Color c) {
      canvas.drawCircle(Offset(x, y), r, Paint()
        ..shader = RadialGradient(colors: [c.withAlpha(80), Colors.transparent]).createShader(
            Rect.fromCircle(center: Offset(x, y), radius: r)));
    }
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height),
        Paint()..color = const Color(0xFF06080F));
    drawOrb(-40 + t * 30, -30 + t * 20, 220, const Color(0xFF6C63FF));
    drawOrb(size.width + 30 - t * 20, 180 + t * 30, 180, const Color(0xFF4ECDC4));
    drawOrb(size.width * 0.3 + t * 10, size.height * 0.7 - t * 15, 150, const Color(0xFF7B2FBE));
    drawOrb(size.width * 0.8 + t * 5, size.height * 0.4 + t * 10, 120, const Color(0xFF06D6A0));

    // Subtle grid lines
    final gridPaint = Paint()..color = Colors.white.withAlpha(6)..strokeWidth = 0.5;
    for (double i = 0; i < size.width; i += 60) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), gridPaint);
    }
    for (double j = 0; j < size.height; j += 60) {
      canvas.drawLine(Offset(0, j), Offset(size.width, j), gridPaint);
    }
  }

  @override
  bool shouldRepaint(_BgPainter old) => old.t != t;
}
