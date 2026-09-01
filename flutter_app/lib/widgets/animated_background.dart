import 'dart:math' as math;
import 'package:flutter/material.dart';


/// Soft, slowly-drifting warm-toned blobs on a cream background —
/// the "dynamic background colour" replacement for the old dark aurora.
/// Pure Flutter animation (AnimationController + CustomPainter), no
/// external packages required.
class AnimatedBackground extends StatefulWidget {
  final Widget child;
  const AnimatedBackground({super.key, required this.child});

  @override
  State<AnimatedBackground> createState() => _AnimatedBackgroundState();
}

class _AnimatedBackgroundState extends State<AnimatedBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          child: Container(color: const Color(0xFFF8F6F1)),
        ),
        Positioned.fill(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, _) {
              return CustomPaint(
                painter: _BlobPainter(progress: _controller.value),
              );
            },
          ),
        ),
        widget.child,
      ],
    );
  }
}

class _BlobPainter extends CustomPainter {
  final double progress; // 0.0 -> 1.0, looping
  _BlobPainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final t = progress * 2 * math.pi;

    _drawBlob(
      canvas,
      size,
      center: Offset(
        size.width * 0.2 + size.width * 0.08 * math.sin(t),
        size.height * 0.15 + size.height * 0.05 * math.cos(t),
      ),
      radius: size.width * 0.35,
      color: const Color(0xFFD8EDDF).withValues(alpha: 0.6), // pale teal-green blob
    );

    _drawBlob(
      canvas,
      size,
      center: Offset(
        size.width * 0.85 + size.width * 0.06 * math.cos(t * 0.8),
        size.height * 0.75 + size.height * 0.06 * math.sin(t * 0.8),
      ),
      radius: size.width * 0.3,
      color: const Color(0xFF5C67F2).withValues(alpha: 0.07), // soft indigo blob
    );

    _drawBlob(
      canvas,
      size,
      center: Offset(
        size.width * 0.5 + size.width * 0.04 * math.sin(t * 1.3),
        size.height * 0.6 + size.height * 0.05 * math.cos(t * 0.9),
      ),
      radius: size.width * 0.25,
      color: const Color(0xFF52B788).withValues(alpha: 0.08), // mid-green blob
    );
  }

  void _drawBlob(
    Canvas canvas,
    Size size, {
    required Offset center,
    required double radius,
    required Color color,
  }) {
    final paint = Paint()
      ..color = color
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 60);
    canvas.drawCircle(center, radius, paint);
  }

  @override
  bool shouldRepaint(covariant _BlobPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
