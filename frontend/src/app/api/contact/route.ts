import { NextRequest, NextResponse } from 'next/server';

// In-memory rate limiting map: ip -> array of submission timestamps
const ipSubmissionTimestamps = new Map<string, number[]>();
const RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000; // 10 minutes
const MAX_SUBMISSIONS_PER_WINDOW = 5;

// Clean up expired rate limiting entries periodically
function cleanupRateLimits(now: number) {
  ipSubmissionTimestamps.forEach((timestamps, ip) => {
    const valid = timestamps.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
    if (valid.length === 0) {
      ipSubmissionTimestamps.delete(ip);
    } else {
      ipSubmissionTimestamps.set(ip, valid);
    }
  });
}

function sanitizeInput(str: string): string {
  if (!str || typeof str !== 'string') return '';
  return str
    .trim()
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;

export async function POST(req: NextRequest) {
  try {
    const now = Date.now();
    cleanupRateLimits(now);

    // Rate Limiting by IP
    const clientIp =
      req.headers.get('x-forwarded-for')?.split(',')[0].trim() ||
      req.headers.get('x-real-ip') ||
      'anonymous-client';

    const currentTimestamps = ipSubmissionTimestamps.get(clientIp) || [];
    const recent = currentTimestamps.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);

    if (recent.length >= MAX_SUBMISSIONS_PER_WINDOW) {
      return NextResponse.json(
        {
          error: 'Rate limit exceeded. Please wait a few minutes before submitting another message.',
        },
        { status: 429 }
      );
    }

    const body = await req.json().catch(() => null);
    if (!body || typeof body !== 'object') {
      return NextResponse.json(
        { error: 'Invalid request payload.' },
        { status: 400 }
      );
    }

    const {
      name,
      email,
      subject,
      message,
      company_website, // Honeypot field
      form_timestamp,  // Time-to-fill check
    } = body;

    // 1. Spam Protection: Honeypot check
    // If the hidden honeypot field is filled, silently ignore and return fake success
    if (company_website && String(company_website).trim() !== '') {
      console.warn(`[Anti-Spam] Bot detected via honeypot trap from IP: ${clientIp}`);
      return NextResponse.json({
        success: true,
        message: 'Your inquiry has been successfully received.',
      });
    }

    // 2. Spam Protection: Minimum time-to-fill check (submitting faster than 2 seconds is bot behavior)
    if (form_timestamp && typeof form_timestamp === 'number') {
      const elapsedMs = now - form_timestamp;
      if (elapsedMs < 2000) {
        return NextResponse.json(
          { error: 'Submission rejected by anti-automation verification.' },
          { status: 400 }
        );
      }
    }

    // 3. Validation & Sanitization
    const sanitizedName = sanitizeInput(name);
    const sanitizedEmail = sanitizeInput(email);
    const sanitizedSubject = sanitizeInput(subject);
    const sanitizedMessage = sanitizeInput(message);

    if (!sanitizedName || sanitizedName.length < 2 || sanitizedName.length > 100) {
      return NextResponse.json(
        { error: 'Please provide a valid name (2 to 100 characters).' },
        { status: 400 }
      );
    }

    if (!sanitizedEmail || !EMAIL_REGEX.test(sanitizedEmail) || sanitizedEmail.length > 120) {
      return NextResponse.json(
        { error: 'Please provide a valid email address.' },
        { status: 400 }
      );
    }

    if (!sanitizedSubject || sanitizedSubject.length < 3 || sanitizedSubject.length > 120) {
      return NextResponse.json(
        { error: 'Please provide a subject line (3 to 120 characters).' },
        { status: 400 }
      );
    }

    if (!sanitizedMessage || sanitizedMessage.length < 10 || sanitizedMessage.length > 3000) {
      return NextResponse.json(
        { error: 'Please provide a message between 10 and 3,000 characters.' },
        { status: 400 }
      );
    }

    // Record submission for rate limiting
    recent.push(now);
    ipSubmissionTimestamps.set(clientIp, recent);

    // 4. Email Notification Dispatch
    // Check if external email provider credentials are configured in server environment
    const resendApiKey = process.env.RESEND_API_KEY;
    const recipientEmail = process.env.CONTACT_EMAIL_TO || 'parthmandore@gmail.com';

    let notificationSent = false;

    if (resendApiKey) {
      try {
        const emailRes = await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${resendApiKey}`,
          },
          body: JSON.stringify({
            from: 'RepoMentor AI Notifications <notifications@repomentor.netlify.app>',
            to: recipientEmail,
            reply_to: sanitizedEmail,
            subject: `[RepoMentor Contact] ${sanitizedSubject}`,
            text: `New Contact Submission from RepoMentor AI:\n\nName: ${sanitizedName}\nEmail: ${sanitizedEmail}\nSubject: ${sanitizedSubject}\n\nMessage:\n${sanitizedMessage}\n\nTimestamp: ${new Date().toISOString()}`,
          }),
        });

        if (emailRes.ok) {
          notificationSent = true;
        } else {
          const errDetail = await emailRes.text().catch(() => '');
          console.error('[Contact Notification Error]', errDetail);
        }
      } catch (emailErr) {
        console.error('[Contact Notification Exception]', emailErr);
      }
    }

    // In local dev or when Resend key is not configured, securely log server-side
    if (!notificationSent) {
      console.log(
        `[Contact Submission Logged Server-Side] Received from "${sanitizedName}" <${sanitizedEmail}>: "${sanitizedSubject}" (${sanitizedMessage.length} chars)`
      );
    }

    return NextResponse.json({
      success: true,
      message: 'Thank you for reaching out! Your message has been received and logged securely.',
    });
  } catch (error: any) {
    console.error('[Contact API Unhandled Error]', error);
    return NextResponse.json(
      { error: 'Internal server error occurred while processing your message.' },
      { status: 500 }
    );
  }
}
