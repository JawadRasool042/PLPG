/**
 * ============================================
 * Email Verification Page - Production Ready
 * ============================================
 * 
 * Facebook-style email verification with:
 * - Verifying state (spinner)
 * - Success state (with auto-redirect)
 * - Expired token state
 * - Invalid token state
 * - Resend verification with rate limiting feedback
 * - Error handling with user-friendly messages
 * 
 * URL Parameters:
 * - token: Verification token from email
 * - email: Pre-fill email for resend form
 * - post_register: "1" after signup redirect
 * - email_sent: "1" or "0" — whether SMTP reported success at registration
 * - success: Flag indicating successful verification
 * - error: Flag indicating error occurred
 * - code: Error code for specific handling
 * - already_verified: User was already verified
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../../config/apiBase';
import { messageFromApiJsonBody } from '../../services/apiError';

// ============================================
// Types and Interfaces
// ============================================
type VerificationStatus = 
  | 'idle'           // No token, show resend form
  | 'verifying'      // API call in progress
  | 'success'        // Successfully verified
  | 'expired'        // Token expired
  | 'invalid'        // Token invalid
  | 'already_verified' // Already verified
  | 'error';         // Generic error

interface VerificationPayload {
  verification_token?: string;
  verification_url?: string;
  dev_note?: string;
}

interface ApiError {
  detail?: string;
  hint?: string;
  error_code?: string;
  email?: string;
  retry_after_seconds?: number;
  email_sent?: boolean;
  dev_fallback?: boolean;
  verification?: VerificationPayload;
  /** Present on 200 from resend when email is not disclosed (anti-enumeration). */
  success?: boolean;
  message?: string;
  missing_settings?: string[];
}

// ============================================
// Constants
// ============================================
const REDIRECT_DELAY_SECONDS = 5;
/** Short UI cooldown only; server enforces real limits (DB + rate limit). */
const RESEND_COOLDOWN_SECONDS = 45;

// ============================================
// Main Component
// ============================================
const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // State management
  const [status, setStatus] = useState<VerificationStatus>('idle');
  const [email, setEmail] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [countdown, setCountdown] = useState(REDIRECT_DELAY_SECONDS);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  /** When set, shown in the green resend banner instead of the default “check inbox” copy. */
  const [resendSuccessDetail, setResendSuccessDetail] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  // URL parameters (trim so email clients / copy-paste quirks do not break verify)
  const token = useMemo(() => {
    const raw = searchParams.get('token');
    if (!raw) return null;
    const t = raw.trim().replace(/^["']+|["']+$/g, '');
    return t.length ? t : null;
  }, [searchParams]);
  const emailFromUrl = searchParams.get('email');
  const postRegister = searchParams.get('post_register') === '1';
  const emailSentFromRegister = searchParams.get('email_sent') === '1';
  const emailSendFailedAfterRegister = postRegister && searchParams.get('email_sent') === '0';
  const successFlag = searchParams.get('success');
  const errorFlag = searchParams.get('error');
  const errorCode = searchParams.get('code');
  const alreadyVerified = searchParams.get('already_verified');

  // ============================================
  // Initialize from URL parameters
  // ============================================
  useEffect(() => {
    if (emailFromUrl) {
      setEmail(decodeURIComponent(emailFromUrl));
    }

    // Handle redirect from backend GET endpoint
    if (successFlag === 'true') {
      if (alreadyVerified === 'true') {
        setStatus('already_verified');
      } else {
        setStatus('success');
      }
      return;
    }

    if (errorFlag === 'true') {
      switch (errorCode) {
        case 'TOKEN_EXPIRED':
          setStatus('expired');
          setErrorMessage('Your verification link has expired. Please request a new one.');
          break;
        case 'INVALID_TOKEN':
          setStatus('invalid');
          setErrorMessage('This verification link is invalid. Please check your email or request a new link.');
          break;
        case 'SERVER_ERROR':
          setStatus('error');
          setErrorMessage('A server error occurred. Please try again later.');
          break;
        default:
          setStatus('error');
          setErrorMessage('Verification failed. Please try again.');
      }
      return;
    }

    // No token and no flags = show resend form
    if (!token) {
      setStatus('idle');
    }
  }, [emailFromUrl, successFlag, errorFlag, errorCode, alreadyVerified, token]);

  // ============================================
  // Verify Token via API
  // ============================================
  useEffect(() => {
    const verifyToken = async () => {
      if (!token || successFlag || errorFlag) return;

      setStatus('verifying');
      setErrorMessage('');

      try {
        const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        });

        const data = await response.json();

        if (response.ok) {
          setStatus('success');
          if (data.email) setEmail(data.email);
        } else {
          const errorData = data as ApiError;
          
          // Set email from response if available
          if (errorData.email) setEmail(errorData.email);
          
          // Handle specific error codes
          switch (errorData.error_code) {
            case 'TOKEN_EXPIRED':
              setStatus('expired');
              setErrorMessage('Your verification link has expired. Request a new one below.');
              break;
            case 'INVALID_TOKEN':
            case 'INVALID_TOKEN_FORMAT':
              setStatus('invalid');
              setErrorMessage('This verification link is invalid or has already been used.');
              break;
            case 'ALREADY_VERIFIED':
              setStatus('already_verified');
              setErrorMessage('Your email is already verified. You can log in now.');
              break;
            default:
              setStatus('error');
              setErrorMessage(errorData.detail || 'Verification failed. Please try again.');
          }
        }
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
        setErrorMessage('Unable to connect to the server. Please check your internet connection.');
      }
    };

    verifyToken();
  }, [token, successFlag, errorFlag]);

  // ============================================
  // Auto-redirect countdown after success
  // ============================================
  useEffect(() => {
    if (status !== 'success' && status !== 'already_verified') return;
    if (countdown <= 0) {
      navigate('/login');
      return;
    }

    const timer = setTimeout(() => {
      setCountdown(prev => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [status, countdown, navigate]);

  // ============================================
  // Resend cooldown timer
  // ============================================
  useEffect(() => {
    if (resendCooldown <= 0) return;

    const timer = setInterval(() => {
      setResendCooldown(prev => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [resendCooldown]);

  // ============================================
  // Handle Resend Verification
  // ============================================
  const handleResendVerification = useCallback(async () => {
    if (!email || resendLoading || resendCooldown > 0) return;

    setResendLoading(true);
    setErrorMessage('');
    setResendSuccess(false);
    setResendSuccessDetail(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        const okData = data as ApiError;
        if (okData.email_sent) {
          setResendSuccess(true);
          setResendSuccessDetail(null);
          setResendCooldown(RESEND_COOLDOWN_SECONDS);
          setTimeout(() => setResendSuccess(false), 8000);
        } else if (okData.dev_fallback && okData.verification?.verification_url) {
          setResendSuccess(true);
          setResendSuccessDetail(
            `Development: open this link to verify your account: ${okData.verification.verification_url}`
          );
          setResendCooldown(RESEND_COOLDOWN_SECONDS);
          setTimeout(() => setResendSuccess(false), 12000);
        } else if (okData.success) {
          // Backend returns 200 + success without email_sent when the address is unknown
          // (anti-enumeration). Do not treat that as an SMTP failure.
          setResendSuccess(true);
          setResendSuccessDetail(
            okData.message ||
              'If an account exists with this email, a verification link has been sent.'
          );
          setResendCooldown(RESEND_COOLDOWN_SECONDS);
          setTimeout(() => setResendSuccess(false), 8000);
        } else {
          setErrorMessage(
            'The server could not confirm that an email was sent. Check backend logs and SMTP settings.'
          );
          setResendSuccess(false);
          setResendCooldown(10);
        }
      } else if (response.status === 429) {
        const retryAfter = data.retry_after_seconds || 300;
        setResendCooldown(retryAfter);
        setErrorMessage(`Please wait ${Math.ceil(retryAfter / 60)} minutes before requesting another email.`);
      } else if (data.error_code === 'ALREADY_VERIFIED') {
        setStatus('already_verified');
      } else {
        const err = data as ApiError;
        const msg = messageFromApiJsonBody(data as Record<string, unknown>, err.detail || 'Failed to send verification email.');
        setErrorMessage(msg);
      }
    } catch (err) {
      console.error('Resend error:', err);
      setErrorMessage('Unable to connect to the server. Please try again.');
    } finally {
      setResendLoading(false);
    }
  }, [email, resendLoading, resendCooldown]);

  // ============================================
  // Format countdown time
  // ============================================
  const formatCooldown = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  // ============================================
  // Render Functions
  // ============================================
  
  // Loading/Verifying State
  const renderVerifying = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center justify-center py-8">
        <div className="relative w-24 h-24 mb-8">
          <div className="absolute inset-0 rounded-full border-4 border-slate-200"></div>
          <div className="absolute inset-0 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Verifying Your Email</h2>
        <p className="text-slate-500 text-center">Please wait while we confirm your email address...</p>
        <div className="mt-6 flex space-x-2">
          <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  );

  // Success State
  const renderSuccess = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10 transform transition-all duration-500">
      <div className="flex flex-col items-center text-center">
        {/* Animated Success Icon */}
        <div className="relative mb-8">
          <div className="w-28 h-28 bg-gradient-to-br from-green-400 via-emerald-500 to-teal-500 rounded-full flex items-center justify-center shadow-2xl">
            <svg className="w-14 h-14 text-white animate-[bounce_1s_ease-in-out_2]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="absolute -top-2 -right-2 text-3xl animate-bounce">🎉</div>
          <div className="absolute -bottom-2 -left-2 text-3xl animate-bounce" style={{ animationDelay: '0.3s' }}>✨</div>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent mb-4">
          Email Verified!
        </h1>
        
        <p className="text-slate-600 text-lg mb-2">
          Welcome to <span className="font-semibold text-indigo-600">PLPG Learning Platform</span>
        </p>
        <p className="text-slate-500 text-sm mb-6">
          Your email has been successfully verified. You can now access all features.
        </p>

        {email && (
          <div className="w-full bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-center text-green-800">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span className="font-medium">{email}</span>
            </div>
          </div>
        )}

        {/* Auto-redirect notice */}
        <div className="w-full bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6">
          <p className="text-indigo-700 text-sm">
            Redirecting to login in <span className="font-bold text-2xl">{countdown}</span> seconds...
          </p>
        </div>

        <Link
          to="/login"
          className="w-full py-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white font-bold rounded-xl hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 text-center text-lg"
        >
          Continue to Login Now →
        </Link>
      </div>
    </div>
  );

  // Already Verified State
  const renderAlreadyVerified = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mb-6">
          <svg className="w-12 h-12 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-3">Already Verified</h1>
        <p className="text-slate-600 mb-6">
          Your email address has already been verified. You can log in to your account.
        </p>

        {/* Auto-redirect notice */}
        <div className="w-full bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <p className="text-blue-700 text-sm">
            Redirecting to login in <span className="font-bold text-xl">{countdown}</span> seconds...
          </p>
        </div>

        <Link
          to="/login"
          className="w-full py-4 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-all duration-300 text-center"
        >
          Go to Login
        </Link>
      </div>
    </div>
  );

  // Expired Token State
  const renderExpired = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-amber-100 rounded-full flex items-center justify-center mb-6">
          <svg className="w-12 h-12 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-3">Link Expired</h1>
        
        <div className="w-full bg-amber-50 border-2 border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-amber-800 font-medium text-sm">
            ⏰ Your verification link has expired for security reasons.
          </p>
        </div>

        <p className="text-slate-600 mb-6">
          Don't worry! Request a new verification email below.
        </p>

        {renderResendForm()}
      </div>
    </div>
  );

  // Invalid Token State
  const renderInvalid = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mb-6">
          <svg className="w-12 h-12 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-3">Invalid Link</h1>
        
        <div className="w-full bg-red-50 border-2 border-red-200 rounded-xl p-4 mb-6">
          <p className="text-red-700 font-medium text-sm">{errorMessage}</p>
        </div>

        <p className="text-slate-600 mb-6">
          The link may have been used already or is malformed. Request a new verification email below.
        </p>

        {renderResendForm()}
      </div>
    </div>
  );

  // Error State
  const renderError = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mb-6">
          <svg className="w-12 h-12 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-3">Verification Failed</h1>
        
        <div className="w-full bg-red-50 border-2 border-red-200 rounded-xl p-4 mb-6">
          <p className="text-red-700 font-medium text-sm">{errorMessage || 'Verification failed. Please try again.'}</p>
        </div>

        <p className="text-slate-600 mb-6">
          Something went wrong. Try requesting a new verification email.
        </p>

        {renderResendForm()}
      </div>
    </div>
  );

  // Idle State (No token - show resend form)
  const renderIdle = () => (
    <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-10">
      <div className="flex flex-col items-center text-center">
        <div className="w-24 h-24 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-6 shadow-xl">
          <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-3">Verify Your Email</h1>

        {emailSendFailedAfterRegister && email && (
          <div className="w-full mb-4 p-4 bg-amber-50 border-2 border-amber-200 rounded-xl text-left text-amber-900 text-sm">
            <p className="font-semibold mb-1">Verification email was not delivered</p>
            <p>
              Your account exists, but the server could not send mail (often Gmail app password, wrong{' '}
              <code className="text-xs bg-amber-100 px-1 rounded">EMAIL_FROM</code>, or SMTP errors). Use{' '}
              <strong>Send verification email</strong> below after fixing backend settings, or check server logs.
            </p>
          </div>
        )}

        <p className="text-slate-600 mb-6">
          {postRegister && emailSentFromRegister && email
            ? `We've sent a verification email to ${email}. Click the link in the email to verify your account.`
            : email
              ? 'Finish signing up by opening the link in your verification email. If nothing arrived, request a new link below.'
              : 'Enter your email address to receive a verification link.'}
        </p>

        {renderResendForm()}

        <div className="w-full mt-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
          <p className="text-slate-600 text-sm">
            <span className="font-semibold">💡 Didn't receive the email?</span>
            <br />
            Check Spam and the Promotions tab, search in All Mail, and confirm the address is correct. If your Gmail is
            the same as the app’s sending address, the message may appear under Sent or All Mail instead of Inbox.
          </p>
        </div>
      </div>
    </div>
  );

  // Resend Form Component (reusable)
  const renderResendForm = () => (
    <div className="w-full">
      {resendSuccess && (
        <div className="mb-4 p-4 bg-green-50 border-2 border-green-300 rounded-xl text-green-700 font-medium text-sm flex items-center">
          <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="break-all text-left">
            {resendSuccessDetail ||
              'Verification email sent! Please check your inbox.'}
          </span>
        </div>
      )}

      {errorMessage && status !== 'expired' && status !== 'invalid' && status !== 'error' && (
        <div className="mb-4 p-4 bg-red-50 border-2 border-red-200 rounded-xl text-red-700 font-medium text-sm">
          {errorMessage}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-left text-sm font-semibold text-slate-700 mb-2">
          Email Address
        </label>
        <div className="relative">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email address"
            className="w-full px-4 py-4 pl-12 border-2 border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all duration-200 outline-none text-slate-900 placeholder-slate-400 font-medium"
          />
          <svg className="absolute left-4 top-4 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
          </svg>
        </div>
      </div>

      <button
        onClick={handleResendVerification}
        disabled={resendLoading || !email || resendCooldown > 0}
        className="w-full py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-2xl hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 mb-4 text-lg"
      >
        {resendLoading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Sending...
          </span>
        ) : resendCooldown > 0 ? (
          `Wait ${formatCooldown(resendCooldown)} to resend`
        ) : (
          'Send Verification Email'
        )}
      </button>

      <Link
        to="/login"
        className="block text-center text-indigo-600 font-semibold hover:text-indigo-700 transition-colors"
      >
        ← Back to Login
      </Link>
    </div>
  );

  // ============================================
  // Main Render
  // ============================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-indigo-50 flex items-center justify-center px-4 sm:px-6 py-12 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-full opacity-30 -mr-48 -mt-48"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-br from-pink-100 to-purple-100 rounded-full opacity-30 -ml-48 -mb-48"></div>

      <div className="relative z-10 w-full max-w-md">
        {status === 'verifying' && renderVerifying()}
        {status === 'success' && renderSuccess()}
        {status === 'already_verified' && renderAlreadyVerified()}
        {status === 'expired' && renderExpired()}
        {status === 'invalid' && renderInvalid()}
        {status === 'error' && renderError()}
        {status === 'idle' && renderIdle()}
      </div>
    </div>
  );
};

export default VerifyEmail;
