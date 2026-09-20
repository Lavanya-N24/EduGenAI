// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:js' as js;

/// Wraps the Google Identity Services One Tap API.
///
/// Shows the "Continue as [name]" popup in the browser corner.
/// Works only on Flutter Web; all methods are no-ops on other platforms.
///
/// ⚠️  SETUP REQUIRED:
/// Replace [webClientId] with the OAuth 2.0 Web Client ID from:
///   Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs
///   (pick the "Web client" entry for project edugenai-11196)
///
/// Also ensure http://localhost and your deployed domain are listed under
/// "Authorized JavaScript origins" for that credential.
class GoogleOneTapService {
  static final GoogleOneTapService instance = GoogleOneTapService._();
  GoogleOneTapService._();

  /// Replace with your actual OAuth Web Client ID from cloud.google.com/console
  /// Project: edugenai-11196
  /// Go to: APIs & Services → Credentials → Web client (auto created by Google)
  static const webClientId =
      '177339568494-raifc6tuvri1o3alu4bm3gj8hfss4uh6.apps.googleusercontent.com';

  Completer<String?>? _completer;

  /// Triggers the One Tap "Continue as [name]" popup.
  /// Returns a [UserCredential] on success, or `null` if dismissed / error.
  Future<UserCredential?> prompt() async {
    if (!kIsWeb) return null;
    if (webClientId.startsWith('YOUR_')) {
      debugPrint('[OneTap] ⚠️  webClientId not set — skipping One Tap');
      return null;
    }

    try {
      final idToken = await _showPrompt();
      if (idToken == null || idToken.isEmpty) return null;

      final cred = GoogleAuthProvider.credential(idToken: idToken);
      return await FirebaseAuth.instance.signInWithCredential(cred);
    } catch (e) {
      debugPrint('[OneTap] Error: $e');
      return null;
    }
  }

  /// Cancels the One Tap prompt if visible.
  void cancel() {
    if (!kIsWeb) return;
    try {
      js.context.callMethod('cancelGoogleOneTap');
    } catch (_) {}
    _completer?.complete(null);
    _completer = null;
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  Future<String?> _showPrompt() {
    _completer?.complete(null); // cancel any previous
    final completer = Completer<String?>();
    _completer = completer;

    // Register Dart callback that JS calls when user taps the account
    js.context['_googleOneTapCallback'] =
        js.allowInterop((dynamic credential) {
      final token = credential?.toString();
      if (!completer.isCompleted) completer.complete(token);
      _completer = null;
      js.context['_googleOneTapCallback'] = null;
      js.context['_googleOneTapCredential'] = null;
    });

    // Was a credential already captured before Dart was ready?
    final existing = js.context['_googleOneTapCredential'];
    if (existing is String && existing.isNotEmpty) {
      js.context['_googleOneTapCredential'] = null;
      completer.complete(existing);
      return completer.future;
    }

    // Trigger the One Tap popup via JS
    try {
      js.context.callMethod('initGoogleOneTap', [webClientId]);
    } catch (e) {
      debugPrint('[OneTap] JS error: $e');
      completer.complete(null);
      return completer.future;
    }

    // Auto-timeout after 90 s (user dismissed or no prompt was shown)
    Future<void>.delayed(const Duration(seconds: 90)).then((_) {
      if (!completer.isCompleted) {
        completer.complete(null);
        _completer = null;
      }
    });

    return completer.future;
  }
}
