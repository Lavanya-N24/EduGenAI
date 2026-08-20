import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

/// API Service — connects Flutter app to the FastAPI backend.
class ApiService {
  static const String baseUrl =
      kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';

  // ── GENERATE: Full Pipeline ─────────────────────────────────
  /// Works on Web (Chrome) and native platforms.
  /// Accepts file as [Uint8List] bytes + [fileName] instead of dart:io File.
  static Future<Map<String, dynamic>> generateFullPipeline({
    String? text,
    Uint8List? fileBytes,
    String? fileName,
    String targetLanguage = 'en',
    bool generateVideo = true,
    String learningMode = 'beginner',
    String userId = 'default_user',
  }) async {
    var uri = Uri.parse('$baseUrl/api/generate/full-pipeline');
    var request = http.MultipartRequest('POST', uri);

    if (text != null && text.isNotEmpty) {
      request.fields['text'] = text;
    }

    if (fileBytes != null && fileName != null) {
      final ext = fileName.split('.').last.toLowerCase();
      MediaType mediaType;
      if (['png', 'jpg', 'jpeg', 'webp'].contains(ext)) {
        mediaType = MediaType('image', ext == 'jpg' ? 'jpeg' : ext);
      } else if (ext == 'pdf') {
        mediaType = MediaType('application', 'pdf');
      } else if (ext == 'docx') {
        mediaType = MediaType('application',
            'vnd.openxmlformats-officedocument.wordprocessingml.document');
      } else if (ext == 'pptx') {
        mediaType = MediaType('application',
            'vnd.openxmlformats-officedocument.presentationml.presentation');
      } else {
        mediaType = MediaType('text', 'plain');
      }

      request.files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: fileName,
        contentType: mediaType,
      ));
    }

    request.fields['target_language'] = targetLanguage;
    request.fields['generate_video_flag'] = generateVideo.toString();
    request.fields['learning_mode'] = learningMode;
    request.fields['user_id'] = userId;

    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Generation failed: ${response.body}');
    }
  }

  // ── GENERATE: Scenes Only (Preview) ──────────────────────
  static Future<Map<String, dynamic>> generateScenesOnly({
    required String text,
    String targetLanguage = 'en',
  }) async {
    var uri = Uri.parse('$baseUrl/api/generate/text-only');
    var request = http.MultipartRequest('POST', uri);
    request.fields['text'] = text;
    request.fields['target_language'] = targetLanguage;

    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Scene generation failed: ${response.body}');
    }
  }

  // ── QUIZ: Generate ────────────────────────────────────────
  static Future<Map<String, dynamic>> generateQuiz({
    required String content,
    int numQuestions = 5,
    String difficulty = 'medium',
    String language = 'en',
  }) async {
    var response = await http.post(
      Uri.parse('$baseUrl/api/quiz/generate'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'content': content,
        'num_questions': numQuestions,
        'difficulty': difficulty,
        'language': language,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Quiz generation failed: ${response.body}');
    }
  }

  // ── QUIZ: Submit Answers ──────────────────────────────────
  static Future<Map<String, dynamic>> submitQuiz({
    required String userId,
    required String topic,
    required List<Map<String, dynamic>> answers,
    String difficulty = 'medium',
  }) async {
    var response = await http.post(
      Uri.parse('$baseUrl/api/quiz/submit'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'topic': topic,
        'answers': answers,
        'difficulty': difficulty,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Quiz submission failed: ${response.body}');
    }
  }

  // ── TUTOR: Chat ───────────────────────────────────────────
  static Future<Map<String, dynamic>> chatWithTutor({
    required String userId,
    required String message,
    required String context,
    List<Map<String, String>> chatHistory = const [],
    String language = 'en',
  }) async {
    var response = await http.post(
      Uri.parse('$baseUrl/api/tutor/chat'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'message': message,
        'context': context,
        'chat_history': chatHistory,
        'language': language,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Tutor chat failed: ${response.body}');
    }
  }

  // ── ANALYTICS ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> getAnalytics(String userId) async {
    var response = await http.get(Uri.parse('$baseUrl/api/analytics/$userId'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Analytics fetch failed: ${response.body}');
    }
  }

  static Future<Map<String, dynamic>> getAnalyticsSummary(
      String userId) async {
    var response =
        await http.get(Uri.parse('$baseUrl/api/analytics/$userId/summary'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Summary fetch failed: ${response.body}');
    }
  }

  // ── SHARING: Create share link ─────────────────────────
  static Future<Map<String, dynamic>> createShareLink({
    required String userId,
    required String filename,
    required String title,
    double duration = 0,
  }) async {
    var response = await http.post(
      Uri.parse('$baseUrl/api/share'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'filename': filename,
        'title': title,
        'duration': duration,
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Share link creation failed: ${response.body}');
    }
  }

  // ── VIDEO HISTORY ───────────────────────────────────
  static Future<Map<String, dynamic>> getUserVideos(String userId) async {
    var response = await http.get(Uri.parse('$baseUrl/api/user/$userId/videos'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Video history fetch failed: ${response.body}');
    }
  }

  // ── LANGUAGES ───────────────────────────────────────
  static Future<Map<String, dynamic>> getLanguages() async {
    var response =
        await http.get(Uri.parse('$baseUrl/api/generate/languages'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Language fetch failed: ${response.body}');
    }
  }
}
