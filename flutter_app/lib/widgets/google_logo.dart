import 'dart:typed_data';
import 'package:flutter/material.dart';

/// Pixel-perfect Google "G" logo using the official SVG paths
/// (viewBox 48×48) converted to Flutter Path bezier curves.
/// No packages, no image assets required.
class GoogleLogoIcon extends StatelessWidget {
  final double size;
  const GoogleLogoIcon({super.key, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _GoogleGPainter()),
    );
  }
}

class _GoogleGPainter extends CustomPainter {
  // Official Google brand colours
  static const _blue   = Color(0xFF4285F4);
  static const _red    = Color(0xFFEA4335);
  static const _yellow = Color(0xFFFBBC05);
  static const _green  = Color(0xFF34A853);

  @override
  void paint(Canvas canvas, Size size) {
    // Scale from the original 48×48 SVG viewBox to the widget size
    final sx = size.width  / 48.0;
    final sy = size.height / 48.0;

    // Column-major 4×4 matrix for Path.transform
    final m = Float64List.fromList([
      sx, 0,  0,  0,
      0,  sy, 0,  0,
      0,  0,  1,  0,
      0,  0,  0,  1,
    ]);

    void draw(Path p, Color c) =>
        canvas.drawPath(p.transform(m), Paint()..color = c);

    // ── Red — top arc ────────────────────────────────────────────────────────
    // SVG: M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85
    //      C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22
    //      l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z
    draw(
      Path()
        ..moveTo(24, 9.5)
        ..cubicTo(27.54, 9.5,   30.71, 10.72, 33.21, 13.10)
        ..lineTo(40.06, 6.25)
        ..cubicTo(35.90, 2.38,  30.47, 0,     24.00,  0)
        ..cubicTo(14.62, 0,      6.51, 5.38,   2.56, 13.22)
        ..lineTo(10.54, 19.41)
        ..cubicTo(12.43, 13.72, 17.74, 9.5,   24.00,  9.5)
        ..close(),
      _red,
    );

    // ── Blue — right side + horizontal crossbar ──────────────────────────────
    // SVG: M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94
    //      c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6
    //      c4.51-4.18 7.09-10.36 7.09-17.65z
    draw(
      Path()
        ..moveTo(46.98, 24.55)
        ..cubicTo(46.98, 22.98, 46.83, 21.46, 46.60, 20.00)
        ..lineTo(24.00, 20.00)
        ..lineTo(24.00, 29.02)
        ..lineTo(36.94, 29.02)
        ..cubicTo(36.36, 31.98, 34.68, 34.50, 32.16, 36.20)
        ..lineTo(39.89, 42.20)
        ..cubicTo(44.40, 38.02, 46.98, 31.84, 46.98, 24.55)
        ..close(),
      _blue,
    );

    // ── Yellow — left arc ────────────────────────────────────────────────────
    // SVG: M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59
    //      s.27-3.14.76-4.59l-7.98-6.19
    //      C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z
    draw(
      Path()
        ..moveTo(10.53, 28.59)
        // c -.48 -1.45 -.76 -2.99 -.76 -4.59
        ..cubicTo(10.05, 27.14,  9.77, 25.60,  9.77, 24.00)
        // s .27 -3.14 .76 -4.59  (smooth cubic — reflected control point)
        ..cubicTo( 9.77, 22.40, 10.04, 20.86, 10.53, 19.41)
        ..lineTo( 2.55, 13.22)
        ..cubicTo( 0.92, 16.46,  0.00, 20.12,  0.00, 24.00)
        ..cubicTo( 0.00, 27.88,  0.92, 31.54,  2.56, 34.78)
        ..lineTo(10.53, 28.59)
        ..close(),
      _yellow,
    );

    // ── Green — bottom arc ───────────────────────────────────────────────────
    // SVG: M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6
    //      c-2.15 1.45-4.92 2.3-8.16 2.3
    //      -6.26 0-11.57-4.22-13.47-9.91
    //      l-7.98 6.19C6.51 42.62 14.62 48 24 48z
    draw(
      Path()
        ..moveTo(24.00, 48.00)
        ..cubicTo(30.48, 48.00, 35.93, 45.87, 39.89, 42.19)
        ..lineTo(32.16, 36.19)
        ..cubicTo(30.01, 37.64, 27.24, 38.49, 24.00, 38.49)
        ..cubicTo(17.74, 38.49, 12.43, 34.27, 10.53, 28.58)
        ..lineTo( 2.55, 34.77)
        ..cubicTo( 6.51, 42.62, 14.62, 48.00, 24.00, 48.00)
        ..close(),
      _green,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}
