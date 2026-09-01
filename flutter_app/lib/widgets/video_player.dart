import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';

/// Full YouTube-style educational video player with responsive controls,
/// mouse hover reveal, play/pause, seek, volume, speed menu, and fullscreen maximize/minimize.
class EduVideoPlayer extends StatefulWidget {
  final String videoUrl;
  final String title;

  const EduVideoPlayer({
    super.key,
    required this.videoUrl,
    this.title = 'EduGenAI Video',
  });

  @override
  State<EduVideoPlayer> createState() => _EduVideoPlayerState();
}

class _EduVideoPlayerState extends State<EduVideoPlayer>
    with SingleTickerProviderStateMixin {
  late VideoPlayerController _controller;
  bool _isInitialized = false;
  bool _hasError = false;
  bool _showControls = true;
  bool _isDragging = false;
  double _volume = 1.0;
  double _playbackSpeed = 1.0;
  Timer? _hideTimer;

  static const _speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

  @override
  void initState() {
    super.initState();
    _initVideo();
  }

  void _initVideo() {
    final url = widget.videoUrl;
    if (url.isEmpty) {
      setState(() => _hasError = true);
      return;
    }

    _controller = VideoPlayerController.networkUrl(Uri.parse(url));
    _controller.initialize().then((_) {
      if (mounted) {
        setState(() => _isInitialized = true);
        _controller.setVolume(_volume);
        _startHideTimer();
      }
    }).catchError((e) {
      debugPrint('Video init error: $e');
      if (mounted) setState(() => _hasError = true);
    });

    _controller.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _hideTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _startHideTimer() {
    _hideTimer?.cancel();
    // Only auto-hide if playing and not dragging
    if (_controller.value.isPlaying && !_isDragging) {
      _hideTimer = Timer(const Duration(seconds: 4), () {
        if (mounted && _controller.value.isPlaying && !_isDragging) {
          setState(() => _showControls = false);
        }
      });
    }
  }

  void _revealControls() {
    if (!_showControls) {
      setState(() => _showControls = true);
    }
    _startHideTimer();
  }

  void _togglePlayPause() {
    setState(() {
      if (_controller.value.isPlaying) {
        _controller.pause();
        _showControls = true;
      } else {
        _controller.play();
        _startHideTimer();
      }
    });
  }

  void _toggleFullscreen() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => _FullScreenVideoPage(
          controller: _controller,
          title: widget.title,
        ),
      ),
    );
    if (mounted) {
      setState(() => _showControls = true);
      _startHideTimer();
    }
  }

  String _fmt(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  void _seek(double ratio) {
    final total = _controller.value.duration.inMilliseconds;
    _controller.seekTo(Duration(milliseconds: (total * ratio).round()));
  }

  @override
  Widget build(BuildContext context) {
    if (!_isInitialized) {
      return _buildPlaceholder();
    }

    final pos = _controller.value.position;
    final dur = _controller.value.duration;
    final ratio = dur.inMilliseconds > 0
        ? (pos.inMilliseconds / dur.inMilliseconds).clamp(0.0, 1.0)
        : 0.0;

    return MouseRegion(
      onHover: (_) => _revealControls(),
      onEnter: (_) => _revealControls(),
      child: Container(
        color: Colors.black,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // ── 1. Video Player Surface ──
            Center(
              child: AspectRatio(
                aspectRatio: _controller.value.aspectRatio > 0
                    ? _controller.value.aspectRatio
                    : 16 / 9,
                child: VideoPlayer(_controller),
              ),
            ),

            // ── 2. Click to Play / Pause Scrim ──
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  if (!_showControls) {
                    _revealControls();
                  } else {
                    _togglePlayPause();
                  }
                },
                child: const SizedBox.expand(),
              ),
            ),

            // ── 3. Controls Layer ──
            AnimatedOpacity(
              opacity: _showControls ? 1.0 : 0.0,
              duration: const Duration(milliseconds: 200),
              child: IgnorePointer(
                ignoring: !_showControls,
                child: Stack(
                  children: [
                    // Dark gradients for readability
                    Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          stops: [0.0, 0.25, 0.7, 1.0],
                          colors: [
                            Color(0xAA000000),
                            Colors.transparent,
                            Colors.transparent,
                            Color(0xCC000000),
                          ],
                        ),
                      ),
                    ),

                    // Top Bar: Title & Speed Menu
                    Positioned(
                      top: 8,
                      left: 12,
                      right: 12,
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              widget.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          _SpeedMenuButton(
                            speeds: _speeds,
                            current: _playbackSpeed,
                            onSelected: (s) {
                              setState(() => _playbackSpeed = s);
                              _controller.setPlaybackSpeed(s);
                              _revealControls();
                            },
                          ),
                        ],
                      ),
                    ),

                    // Center Big Play / Pause Button
                    Center(
                      child: GestureDetector(
                        onTap: _togglePlayPause,
                        child: Container(
                          decoration: const BoxDecoration(
                            color: Colors.black54,
                            shape: BoxShape.circle,
                          ),
                          padding: const EdgeInsets.all(12),
                          child: Icon(
                            _controller.value.isPlaying
                                ? Icons.pause_rounded
                                : Icons.play_arrow_rounded,
                            color: Colors.white,
                            size: 44,
                          ),
                        ),
                      ),
                    ),

                    // Bottom Bar: Slider & Controls
                    Positioned(
                      bottom: 0,
                      left: 0,
                      right: 0,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            // Seek Slider
                            SliderTheme(
                              data: SliderTheme.of(context).copyWith(
                                trackHeight: 3.5,
                                thumbShape: const RoundSliderThumbShape(
                                    enabledThumbRadius: 6),
                                overlayShape: const RoundSliderOverlayShape(
                                    overlayRadius: 12),
                                activeTrackColor: const Color(0xFFD97706),
                                inactiveTrackColor: Colors.white30,
                                thumbColor: const Color(0xFFD97706),
                              ),
                              child: Slider(
                                value: ratio,
                                onChangeStart: (_) {
                                  _isDragging = true;
                                  _hideTimer?.cancel();
                                },
                                onChanged: (v) {
                                  _seek(v);
                                },
                                onChangeEnd: (_) {
                                  _isDragging = false;
                                  _startHideTimer();
                                },
                              ),
                            ),

                            // Controls Row
                            Row(
                              children: [
                                // Play / Pause Mini Button
                                IconButton(
                                  icon: Icon(
                                    _controller.value.isPlaying
                                        ? Icons.pause_rounded
                                        : Icons.play_arrow_rounded,
                                    color: Colors.white,
                                    size: 24,
                                  ),
                                  onPressed: _togglePlayPause,
                                ),

                                const SizedBox(width: 4),

                                // Timestamp
                                Text(
                                  '${_fmt(pos)} / ${_fmt(dur)}',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                  ),
                                ),

                                const Spacer(),

                                // Volume Slider Control
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      _volume == 0
                                          ? Icons.volume_off_rounded
                                          : (_volume < 0.5
                                              ? Icons.volume_down_rounded
                                              : Icons.volume_up_rounded),
                                      color: Colors.white,
                                      size: 20,
                                    ),
                                    SizedBox(
                                      width: 70,
                                      child: SliderTheme(
                                        data: SliderTheme.of(context).copyWith(
                                          trackHeight: 2.5,
                                          thumbShape:
                                              const RoundSliderThumbShape(
                                                  enabledThumbRadius: 4),
                                          activeTrackColor: Colors.white,
                                          inactiveTrackColor: Colors.white24,
                                          thumbColor: Colors.white,
                                        ),
                                        child: Slider(
                                          value: _volume,
                                          onChanged: (v) {
                                            setState(() => _volume = v);
                                            _controller.setVolume(v);
                                            _revealControls();
                                          },
                                        ),
                                      ),
                                    ),
                                  ],
                                ),

                                const SizedBox(width: 6),

                                // Fullscreen Button
                                IconButton(
                                  tooltip: 'Maximize Fullscreen',
                                  icon: const Icon(
                                    Icons.fullscreen_rounded,
                                    color: Colors.white,
                                    size: 26,
                                  ),
                                  onPressed: _toggleFullscreen,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Replay Badge at Video End
            if (_isInitialized &&
                !_controller.value.isPlaying &&
                pos >= dur &&
                dur > Duration.zero)
              GestureDetector(
                onTap: () {
                  _controller.seekTo(Duration.zero);
                  _controller.play();
                  _startHideTimer();
                },
                child: Container(
                  decoration: const BoxDecoration(
                    color: Colors.black87,
                    shape: BoxShape.circle,
                  ),
                  padding: const EdgeInsets.all(16),
                  child: const Icon(
                    Icons.replay_rounded,
                    color: Color(0xFFD97706),
                    size: 48,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      color: Colors.black,
      child: Center(
        child: _hasError
            ? Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline_rounded,
                      color: Colors.redAccent, size: 48),
                  const SizedBox(height: 12),
                  const Text('Could not load video',
                      style: TextStyle(color: Colors.white54)),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _hasError = false;
                        _isInitialized = false;
                      });
                      _initVideo();
                    },
                    child: const Text('Retry',
                        style: TextStyle(color: Color(0xFFD97706))),
                  ),
                ],
              )
            : const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: Color(0xFFD97706)),
                  SizedBox(height: 14),
                  Text('Loading video…',
                      style: TextStyle(color: Colors.white54, fontSize: 13)),
                ],
              ),
      ),
    );
  }
}

class _SpeedMenuButton extends StatelessWidget {
  final List<double> speeds;
  final double current;
  final ValueChanged<double> onSelected;

  const _SpeedMenuButton({
    required this.speeds,
    required this.current,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<double>(
      tooltip: 'Playback speed',
      color: const Color(0xFF1E1E1D),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      itemBuilder: (_) => speeds
          .map(
            (s) => PopupMenuItem<double>(
              value: s,
              child: Row(
                children: [
                  Icon(
                    Icons.check,
                    size: 16,
                    color: s == current
                        ? const Color(0xFFD97706)
                        : Colors.transparent,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    s == 1.0 ? 'Normal (1x)' : '${s}x',
                    style: TextStyle(
                      color: s == current
                          ? const Color(0xFFD97706)
                          : Colors.white,
                      fontSize: 13,
                      fontWeight:
                          s == current ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(),
      onSelected: onSelected,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.black45,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.speed_rounded, color: Colors.white, size: 16),
            const SizedBox(width: 4),
            Text(
              current == 1.0 ? '1x' : '${current}x',
              style: const TextStyle(color: Colors.white, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

/// Dedicated Fullscreen Page with Minimize & Back Arrow Navigation
class _FullScreenVideoPage extends StatefulWidget {
  final VideoPlayerController controller;
  final String title;

  const _FullScreenVideoPage({
    required this.controller,
    required this.title,
  });

  @override
  State<_FullScreenVideoPage> createState() => _FullScreenVideoPageState();
}

class _FullScreenVideoPageState extends State<_FullScreenVideoPage> {
  bool _showControls = true;
  bool _isDragging = false;
  double _volume = 1.0;
  double _playbackSpeed = 1.0;
  Timer? _hideTimer;

  static const _speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
      DeviceOrientation.portraitUp,
    ]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

    widget.controller.addListener(_onControllerUpdate);
    _startHideTimer();
  }

  void _onControllerUpdate() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _hideTimer?.cancel();
    widget.controller.removeListener(_onControllerUpdate);
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    super.dispose();
  }

  void _startHideTimer() {
    _hideTimer?.cancel();
    if (widget.controller.value.isPlaying && !_isDragging) {
      _hideTimer = Timer(const Duration(seconds: 4), () {
        if (mounted && widget.controller.value.isPlaying && !_isDragging) {
          setState(() => _showControls = false);
        }
      });
    }
  }

  void _revealControls() {
    if (!_showControls) {
      setState(() => _showControls = true);
    }
    _startHideTimer();
  }

  void _togglePlayPause() {
    setState(() {
      if (widget.controller.value.isPlaying) {
        widget.controller.pause();
        _showControls = true;
      } else {
        widget.controller.play();
        _startHideTimer();
      }
    });
  }

  String _fmt(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  void _seek(double ratio) {
    final total = widget.controller.value.duration.inMilliseconds;
    widget.controller.seekTo(Duration(milliseconds: (total * ratio).round()));
  }

  @override
  Widget build(BuildContext context) {
    final pos = widget.controller.value.position;
    final dur = widget.controller.value.duration;
    final ratio = dur.inMilliseconds > 0
        ? (pos.inMilliseconds / dur.inMilliseconds).clamp(0.0, 1.0)
        : 0.0;

    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, result) {
        SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
        SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: MouseRegion(
          onHover: (_) => _revealControls(),
          onEnter: (_) => _revealControls(),
          child: Stack(
            alignment: Alignment.center,
            children: [
              // ── 1. Video Layer ──
              Center(
                child: AspectRatio(
                  aspectRatio: widget.controller.value.aspectRatio > 0
                      ? widget.controller.value.aspectRatio
                      : 16 / 9,
                  child: VideoPlayer(widget.controller),
                ),
              ),

              // ── 2. Click Scrim ──
              Positioned.fill(
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () {
                    if (!_showControls) {
                      _revealControls();
                    } else {
                      _togglePlayPause();
                    }
                  },
                  child: const SizedBox.expand(),
                ),
              ),

              // ── 3. Fullscreen Controls ──
              AnimatedOpacity(
                opacity: _showControls ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 200),
                child: IgnorePointer(
                  ignoring: !_showControls,
                  child: Stack(
                    children: [
                      // Gradient
                      Container(
                        decoration: const BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            stops: [0.0, 0.25, 0.75, 1.0],
                            colors: [
                              Color(0xCC000000),
                              Colors.transparent,
                              Colors.transparent,
                              Color(0xCC000000),
                            ],
                          ),
                        ),
                      ),

                      // Top Bar with Back / Minimize Arrow
                      Positioned(
                        top: 0,
                        left: 0,
                        right: 0,
                        child: SafeArea(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 8),
                            child: Row(
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.arrow_back_rounded,
                                      color: Colors.white, size: 28),
                                  tooltip: 'Minimize / Exit fullscreen',
                                  onPressed: () => Navigator.pop(context),
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    widget.title,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                _SpeedMenuButton(
                                  speeds: _speeds,
                                  current: _playbackSpeed,
                                  onSelected: (s) {
                                    setState(() => _playbackSpeed = s);
                                    widget.controller.setPlaybackSpeed(s);
                                    _revealControls();
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                      // Center Play / Pause
                      Center(
                        child: GestureDetector(
                          onTap: _togglePlayPause,
                          child: Container(
                            decoration: const BoxDecoration(
                              color: Colors.black54,
                              shape: BoxShape.circle,
                            ),
                            padding: const EdgeInsets.all(16),
                            child: Icon(
                              widget.controller.value.isPlaying
                                  ? Icons.pause_rounded
                                  : Icons.play_arrow_rounded,
                              color: Colors.white,
                              size: 54,
                            ),
                          ),
                        ),
                      ),

                      // Bottom Bar
                      Positioned(
                        bottom: 0,
                        left: 0,
                        right: 0,
                        child: SafeArea(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SliderTheme(
                                  data: SliderTheme.of(context).copyWith(
                                    trackHeight: 4.0,
                                    thumbShape:
                                        const RoundSliderThumbShape(
                                            enabledThumbRadius: 7),
                                    activeTrackColor: const Color(0xFFD97706),
                                    inactiveTrackColor: Colors.white30,
                                    thumbColor: const Color(0xFFD97706),
                                  ),
                                  child: Slider(
                                    value: ratio,
                                    onChangeStart: (_) {
                                      _isDragging = true;
                                      _hideTimer?.cancel();
                                    },
                                    onChanged: (v) {
                                      _seek(v);
                                    },
                                    onChangeEnd: (_) {
                                      _isDragging = false;
                                      _startHideTimer();
                                    },
                                  ),
                                ),
                                Row(
                                  children: [
                                    IconButton(
                                      icon: Icon(
                                        widget.controller.value.isPlaying
                                            ? Icons.pause_rounded
                                            : Icons.play_arrow_rounded,
                                        color: Colors.white,
                                        size: 28,
                                      ),
                                      onPressed: _togglePlayPause,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      '${_fmt(pos)} / ${_fmt(dur)}',
                                      style: const TextStyle(
                                          color: Colors.white, fontSize: 13),
                                    ),
                                    const Spacer(),
                                    // Fullscreen Volume Control
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(
                                          _volume == 0
                                              ? Icons.volume_off_rounded
                                              : (_volume < 0.5
                                                  ? Icons.volume_down_rounded
                                                  : Icons.volume_up_rounded),
                                          color: Colors.white,
                                          size: 20,
                                        ),
                                        SizedBox(
                                          width: 80,
                                          child: SliderTheme(
                                            data: SliderTheme.of(context).copyWith(
                                              trackHeight: 3.0,
                                              thumbShape:
                                                  const RoundSliderThumbShape(
                                                      enabledThumbRadius: 5),
                                              activeTrackColor: Colors.white,
                                              inactiveTrackColor: Colors.white24,
                                              thumbColor: Colors.white,
                                            ),
                                            child: Slider(
                                              value: _volume,
                                              onChanged: (v) {
                                                setState(() => _volume = v);
                                                widget.controller.setVolume(v);
                                                _revealControls();
                                              },
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(width: 8),
                                    IconButton(
                                      tooltip: 'Exit Fullscreen (Minimize)',
                                      icon: const Icon(
                                          Icons.fullscreen_exit_rounded,
                                          color: Colors.white,
                                          size: 30),
                                      onPressed: () => Navigator.pop(context),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
