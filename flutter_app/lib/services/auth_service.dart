import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AppUser {
  final String id;
  final String email;
  final String name;
  final String? photoUrl;
  final bool isNewUser;

  AppUser({
    required this.id,
    required this.email,
    required this.name,
    this.photoUrl,
    this.isNewUser = false,
  });
}

// Alias to prevent naming conflicts with older references
typedef UserModel = AppUser;

class AuthService {
  static final AuthService instance = AuthService._();
  AuthService._();

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  GoogleSignIn? _googleSignIn;

  GoogleSignIn get _mobileGoogleSignIn =>
      _googleSignIn ??= GoogleSignIn(scopes: ['email', 'profile']);

  AppUser? get currentUser {
    final user = _auth.currentUser;
    if (user == null) return null;
    return AppUser(
      id: user.uid,
      email: user.email ?? '',
      name: user.displayName ?? (user.email != null ? user.email!.split('@')[0] : 'Learner'),
      photoUrl: user.photoURL,
    );
  }

  // ── Sync User Profile with Firestore ──
  Future<bool> _saveUserToFirestore(User user) async {
    try {
      final userDocRef = _firestore.collection('users').doc(user.uid);
      final docSnapshot = await userDocRef.get();

      if (!docSnapshot.exists) {
        await userDocRef.set({
          'uid': user.uid,
          'email': user.email ?? '',
          'displayName': user.displayName ?? (user.email != null ? user.email!.split('@')[0] : 'Learner'),
          'photoURL': user.photoURL ?? '',
          'theme': 'cream',
          'plan': 'free',
          'createdAt': FieldValue.serverTimestamp(),
          'lastLoginAt': FieldValue.serverTimestamp(),
        });
        return true; // Is new user
      } else {
        await userDocRef.update({
          'lastLoginAt': FieldValue.serverTimestamp(),
          if (user.displayName != null) 'displayName': user.displayName,
          if (user.photoURL != null) 'photoURL': user.photoURL,
        });
        return false; // Existing user
      }
    } catch (e) {
      debugPrint('Firestore Sync Error: $e');
      return false;
    }
  }

  // ── Update Theme in Firestore ──
  Future<void> updateThemeInDatabase(String themeName) async {
    final user = _auth.currentUser;
    if (user == null) return;
    try {
      await _firestore.collection('users').doc(user.uid).update({
        'theme': themeName.toLowerCase(),
      });
    } catch (e) {
      debugPrint('Error updating theme in database: $e');
    }
  }

  // ── Save User Details on Onboarding ──
  Future<void> saveUserProfileDetails({
    required String name,
    required String age,
    required String role,
    required String goal,
  }) async {
    final user = _auth.currentUser;
    if (user == null) return;

    try {
      await user.updateDisplayName(name);
      await _firestore.collection('users').doc(user.uid).update({
        'displayName': name,
        'age': age,
        'role': role,
        'learningGoal': goal,
        'profileCompleted': true,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      debugPrint('Error saving user profile details: $e');
      rethrow;
    }
  }

  // ── Google Sign-In ──
  Future<AppUser?> signInWithGoogle() async {
    try {
      UserCredential userCredential;

      if (kIsWeb) {
        final GoogleAuthProvider googleProvider = GoogleAuthProvider();
        googleProvider.addScope('email');
        googleProvider.addScope('profile');
        googleProvider.setCustomParameters({'prompt': 'select_account'});
        userCredential = await _auth.signInWithPopup(googleProvider);
      } else {
        final GoogleSignInAccount? googleUser = await _mobileGoogleSignIn.signIn();
        if (googleUser == null) return null;

        final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
        final AuthCredential credential = GoogleAuthProvider.credential(
          accessToken: googleAuth.accessToken,
          idToken: googleAuth.idToken,
        );
        userCredential = await _auth.signInWithCredential(credential);
      }

      final user = userCredential.user;
      if (user == null) return null;

      final isNew = await _saveUserToFirestore(user);

      return AppUser(
        id: user.uid,
        email: user.email ?? '',
        name: user.displayName ?? (user.email != null ? user.email!.split('@')[0] : 'Learner'),
        photoUrl: user.photoURL,
        isNewUser: isNew,
      );
    } catch (e) {
      debugPrint('Google Sign-In Error: $e');
      rethrow;
    }
  }

  // ── Email / Password Auth ──
  Future<AppUser?> signUpWithEmail(String email, String password, String name) async {
    final cred = await _auth.createUserWithEmailAndPassword(email: email, password: password);
    if (cred.user != null) {
      await cred.user!.updateDisplayName(name);
      await _saveUserToFirestore(cred.user!);
      return AppUser(id: cred.user!.uid, email: email, name: name, isNewUser: true);
    }
    return null;
  }

  Future<AppUser?> signInWithEmail(String email, String password) async {
    final cred = await _auth.signInWithEmailAndPassword(email: email, password: password);
    if (cred.user != null) {
      await _saveUserToFirestore(cred.user!);
      return AppUser(
        id: cred.user!.uid,
        email: email,
        name: cred.user!.displayName ?? email.split('@')[0],
        isNewUser: false,
      );
    }
    return null;
  }

  Future<void> signOut() async {
    if (!kIsWeb) {
      try {
        await _mobileGoogleSignIn.signOut();
      } catch (_) {}
    }
    await _auth.signOut();
  }

  // ── Local In-Memory & Firestore History CRUD Operations ──
  static final List<Map<String, dynamic>> _localHistory = [];

  Future<void> saveHistoryItem({
    required String title,
    required String mode,
    required Map<String, dynamic> generationData,
  }) async {
    final newItem = {
      'id': 'local_${DateTime.now().millisecondsSinceEpoch}',
      'title': title,
      'mode': mode,
      'isPinned': false,
      'createdAt': DateTime.now().toIso8601String(),
      'data': generationData,
    };

    // Avoid exact duplicates
    _localHistory.removeWhere((item) => item['title'] == title && item['mode'] == mode);
    _localHistory.insert(0, newItem);

    final user = _auth.currentUser;
    if (user != null) {
      try {
        await _firestore
            .collection('users')
            .doc(user.uid)
            .collection('history')
            .add({
          'title': title,
          'mode': mode,
          'isPinned': false,
          'createdAt': FieldValue.serverTimestamp(),
          'data': generationData,
        });
      } catch (e) {
        debugPrint('Error saving history to Firestore: $e');
      }
    }
  }

  Stream<QuerySnapshot<Map<String, dynamic>>> getUserHistoryStream() {
    final user = _auth.currentUser;
    if (user != null) {
      try {
        return _firestore
            .collection('users')
            .doc(user.uid)
            .collection('history')
            .orderBy('createdAt', descending: true)
            .snapshots();
      } catch (_) {}
    }
    return const Stream.empty();
  }

  List<Map<String, dynamic>> getLocalHistory() {
    return List.unmodifiable(_localHistory);
  }

  Future<void> togglePinHistoryItem(String docId, bool currentPinState) async {
    for (var item in _localHistory) {
      if (item['id'] == docId) {
        item['isPinned'] = !currentPinState;
        break;
      }
    }

    final user = _auth.currentUser;
    if (user != null && !docId.startsWith('local_')) {
      try {
        await _firestore
            .collection('users')
            .doc(user.uid)
            .collection('history')
            .doc(docId)
            .update({'isPinned': !currentPinState});
      } catch (e) {
        debugPrint('Error toggling pin in Firestore: $e');
      }
    }
  }

  Future<void> deleteHistoryItem(String docId) async {
    _localHistory.removeWhere((item) => item['id'] == docId);

    final user = _auth.currentUser;
    if (user != null && !docId.startsWith('local_')) {
      try {
        await _firestore
            .collection('users')
            .doc(user.uid)
            .collection('history')
            .doc(docId)
            .delete();
      } catch (e) {
        debugPrint('Error deleting history in Firestore: $e');
      }
    }
  }
}