import 'package:flutter/material.dart';
import 'animated_background.dart';

class DynamicBackground extends StatelessWidget {
  final Widget? child;
  const DynamicBackground({super.key, this.child});

  @override
  Widget build(BuildContext context) {
    return AnimatedBackground(
      child: child ?? const SizedBox.expand(),
    );
  }
}
