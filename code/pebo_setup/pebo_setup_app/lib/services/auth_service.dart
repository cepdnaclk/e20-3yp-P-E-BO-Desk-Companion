import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();

  User? get currentUser => _auth.currentUser;
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // Email/Password Sign In
  Future<User?> signInWithEmailPassword(String email, String password) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      return credential.user;
    } on FirebaseAuthException catch (e) {
      throw e.message ?? 'Authentication failed';
    }
  }

  // Modified Google Sign In method
  Future<User?> signInWithGoogle() async {
    try {
      // Show loading state before attempt
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();

      // User canceled the sign-in flow
      if (googleUser == null) {
        throw 'Sign in canceled by user';
      }

      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;

      // Check if we got the tokens
      if (googleAuth.accessToken == null || googleAuth.idToken == null) {
        throw 'Could not get auth tokens';
      }

      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await _auth.signInWithCredential(credential);
      return userCredential.user;
    } catch (e) {
      print('Google sign in error: $e');
      throw 'Google sign in failed: $e';
    }
  }
  // Email Registration
  Future<User?> registerWithEmailPassword(String email, String password) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      return credential.user;
    } on FirebaseAuthException catch (e) {
      throw e.message ?? 'Registration failed';
    }
  }

  // Update User Profile
  Future<void> updateUserProfile(String displayName) async {
    await _auth.currentUser?.updateDisplayName(displayName);
  }

  // Sign Out
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    await _auth.signOut();
  }

  // Connect PEBO Device
  Future<bool> connectPeboDevice(String deviceId, String password) async {
    try {
      // Simulate a network request (replace with real API call)
      await Future.delayed(const Duration(seconds: 2));

      // Replace this with actual validation logic (e.g., check credentials in Firebase)
      if (deviceId.isNotEmpty && password.isNotEmpty) {
        return true; // Connection successful
      } else {
        return false; // Connection failed
      }
    } catch (e) {
      return false;
    }
  }
}
