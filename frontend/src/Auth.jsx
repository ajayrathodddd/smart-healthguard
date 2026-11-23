
import { useState } from "react";
import {
  Activity,
  Mail,
  LockKeyhole,
  User,
  ArrowLeft,
  ShieldCheck,
  Eye,
  EyeOff,
} from "lucide-react";

import "./Auth.css";

import {
  auth,
  googleProvider,
  signInWithPopup,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut,
} from "./firebase";

function Auth() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  const getErrorMessage = (err) => {
    const messages = {
      "auth/email-already-in-use": "This email is already registered. Please log in.",
      "auth/invalid-email": "Please enter a valid email address.",
      "auth/weak-password": "Password must contain at least 6 characters.",
      "auth/invalid-credential": "Incorrect email or password.",
      "auth/user-not-found": "No account found with this email.",
      "auth/wrong-password": "Incorrect password.",
      "auth/popup-closed-by-user": "Google sign-in was cancelled.",
      "auth/popup-blocked": "Your browser blocked the Google sign-in popup.",
      "auth/too-many-requests": "Too many attempts. Please try again later.",
      "auth/network-request-failed": "Network error. Check your internet connection.",
    };

    return messages[err.code] || err.message || "Something went wrong. Please try again.";
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    clearMessages();

    if (!name.trim()) {
      setError("Please enter your full name.");
      return;
    }

    if (password.length < 6) {
      setError("Password must contain at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      const result = await createUserWithEmailAndPassword(
        auth,
        email.trim(),
        password
      );

      await sendEmailVerification(result.user);
      await signOut(auth);

      setMessage(
        "Your account has been created! Check your email and click the verification link before logging in."
      );
      setMode("login");
      setPassword("");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);

    try {
      const result = await signInWithEmailAndPassword(
        auth,
        email.trim(),
        password
      );

      if (!result.user.emailVerified) {
        await sendEmailVerification(result.user);
        await signOut(auth);
        setError(
          "Your email is not verified yet. We sent another verification link. Please check your inbox."
        );
        return;
      }

      setMessage("Login successful. Welcome to Smart HealthGuard!");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    clearMessages();
    setLoading(true);

    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    clearMessages();

    if (!email.trim()) {
      setError("Please enter your email address first.");
      return;
    }

    setLoading(true);

    try {
      await sendPasswordResetEmail(auth, email.trim());
      setMessage("Password reset email sent. Please check your inbox.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (nextMode) => {
    clearMessages();
    setPassword("");
    setShowPassword(false);
    setMode(nextMode);
  };

  return (
    <div className="auth-container">
      <div className="auth-mobile-brand" aria-label="Smart HealthGuard">
        <div className="auth-mobile-shield">
          <ShieldCheck size={24} />
        </div>
        <div>
          <strong>Smart HealthGuard <span>AI</span></strong>
          <small>Medicine Safety &amp; Health Awareness</small>
        </div>
      </div>

      <div className="auth-layout">

        <section className="auth-visual">
          <div className="visual-brand">
            <div className="visual-logo">
              <Activity size={42} />
            </div>

            <div>
              <h1>Smart<br />HealthGuard</h1>
              <p>Your smart companion for medicine information and health awareness</p>
            </div>
          </div>

          <div className="visual-image">
            <img
              src="/healthguard-illustration.png"
              alt="Healthcare doctor and medical protection illustration"
            />
          </div>

          <div className="visual-features">
            <p><ShieldCheck size={19} /> Learn about medicines</p>
            <p><ShieldCheck size={19} /> Scan and analyze products</p>
            <p><ShieldCheck size={19} /> Stay informed, stay healthy</p>
          </div>
        </section>

        <section className="auth-card">
          <div className="auth-brand">
            <div className="auth-logo">
              <ShieldCheck size={31} />
            </div>
          </div>

          {mode !== "forgot" && (
            <div className="auth-tabs">
              <button
                type="button"
                className={mode === "login" ? "active" : ""}
                onClick={() => switchMode("login")}
              >
                Welcome Back
              </button>

              <button
                type="button"
                className={mode === "signup" ? "active" : ""}
                onClick={() => switchMode("signup")}
              >
                Create Account
              </button>
            </div>
          )}

          {mode === "forgot" ? (
            <>
              <h3>Reset your password</h3>
              <p className="auth-description">
                Enter your registered email to receive a password reset link.
              </p>

              <form className="auth-form" onSubmit={handleForgotPassword}>
                <label htmlFor="auth-email">Email address</label>
                <div className="auth-input-wrapper">
                  <Mail size={19} />
                  <input
                    id="auth-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email address"
                    required
                  />
                </div>

                {error && <p className="auth-error">{error}</p>}
                {message && <p className="auth-message">{message}</p>}

                <button className="auth-primary-button" type="submit" disabled={loading}>
                  {loading ? "Sending..." : "Send reset link"}
                </button>
              </form>

              <button
                className="auth-back-button"
                type="button"
                onClick={() => switchMode("login")}
              >
                <ArrowLeft size={17} /> Back to login
              </button>
            </>
          ) : (
            <>
              <h3>{mode === "signup" ? "Create Account" : "Welcome Back!"}</h3>

              <p className="auth-description">
                {mode === "signup"
                  ? "Create your Smart HealthGuard account"
                  : "Login to your Smart HealthGuard account"}
              </p>

              <form
                className="auth-form"
                onSubmit={mode === "signup" ? handleSignup : handleLogin}
              >
                {mode === "signup" && (
                  <>
                    <label htmlFor="auth-name">Full Name</label>
                    <div className="auth-input-wrapper">
                      <User size={19} />
                      <input
                        id="auth-name"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Full Name"
                        required
                      />
                    </div>
                  </>
                )}

                <label htmlFor="auth-email">Email address</label>
                <div className="auth-input-wrapper">
                  <Mail size={19} />
                  <input
                    id="auth-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email address"
                    required
                  />
                </div>

                <label htmlFor="auth-password">Password</label>
                <div className="auth-input-wrapper">
                  <LockKeyhole size={19} />
                  <input
                    id="auth-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    minLength={6}
                    required
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>

                {mode === "login" && (
                  <div className="auth-login-options">
                    <label className="auth-remember">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(event) => setRememberMe(event.target.checked)}
                      />
                      <span>Remember me</span>
                    </label>
                    <button type="button" onClick={() => switchMode("forgot")}>
                      Forgot password?
                    </button>
                  </div>
                )}

                {error && <p className="auth-error">{error}</p>}
                {message && <p className="auth-message">{message}</p>}

                <button
                  className="auth-primary-button"
                  type="submit"
                  disabled={loading}
                >
                  {loading
                    ? "Please wait..."
                    : mode === "signup"
                      ? "Create account"
                      : "Log in"}
                </button>
              </form>

              <div className="auth-divider"><span>OR</span></div>

              <button
                className="auth-google-button"
                type="button"
                onClick={handleGoogleLogin}
                disabled={loading}
              >
                <span className="google-g">G</span>
                Continue with Google
              </button>

              <p className="auth-switch">
                {mode === "signup"
                  ? "Already have an account? "
                  : "Don't have an account? "}
                <button
                  type="button"
                  onClick={() => switchMode(mode === "signup" ? "login" : "signup")}
                >
                  {mode === "signup" ? "Log in" : "Sign up"}
                </button>
              </p>
            </>
          )}

          <div className="auth-footer">
            <ShieldCheck size={23} />
            <p>
              Smart HealthGuard provides educational information, not medical
              diagnosis or prescriptions.
            </p>
           </div>
        </section>
      </div>

      <footer className="copyright-footer">
        © Rathod.in. All rights reserved.
      </footer>
    </div>
  );
}

export default Auth;
