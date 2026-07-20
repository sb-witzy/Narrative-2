// Shared helpers for Print and Email actions across narratives and appeal letters.
// - printLetter: opens a print-friendly window with clean typography and triggers the OS print dialog.
// - emailLetter: builds a mailto: link that opens the user's default mail client (usually Outlook).
//   If the letter is too long for a mailto URL, the body is placed on the clipboard and a shorter
//   note is used instead, so the user can Ctrl+V into the email body.

import { toast } from "sonner";

const MAILTO_URL_LIMIT = 1900; // safe cross-client ceiling incl. subject overhead

/**
 * Robust "copy to clipboard" that works on plain HTTP LAN URLs.
 *
 * `navigator.clipboard.writeText` is only available in secure contexts
 * (HTTPS or localhost). When staff hit the app at http://<server-ip>:8080
 * we must fall back to the legacy document.execCommand('copy') path.
 * Returns true on success, false otherwise.
 */
export async function copyText(text) {
  if (!text) return false;
  // Modern path (HTTPS / localhost)
  if (typeof navigator !== "undefined" && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch { /* fall through */ }
  }
  // Legacy path — works on http:// LAN URLs
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    ta.style.left = "-9999px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Open a minimal HTML window with the letter and trigger the print dialog.
 * @param {{title?: string, subject?: string, body: string}} args
 */
export function printLetter({ title = "Narrative.Rx", subject, body }) {
  if (!body || !body.trim()) {
    toast.error("Nothing to print yet");
    return;
  }
  const w = window.open("", "_blank", "width=820,height=760");
  if (!w) {
    toast.error("Popup blocked — allow pop-ups for this site and try again");
    return;
  }
  const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  html, body { margin: 0; padding: 0; background: white; color: #1a1a1a; }
  body { font-family: Georgia, "Times New Roman", serif; line-height: 1.55; }
  .page { max-width: 720px; margin: 48px auto; padding: 0 32px; }
  .subject { font-weight: 700; font-size: 15px; letter-spacing: 0.02em; text-transform: uppercase; color: #555; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #ddd; }
  pre { white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 15px; margin: 0; }
  @media print {
    .page { margin: 0; padding: 24px; max-width: none; }
    @page { margin: 0.75in; }
  }
</style>
</head>
<body>
  <div class="page">
    ${subject ? `<div class="subject">${escapeHtml(subject)}</div>` : ""}
    <pre>${escapeHtml(body)}</pre>
  </div>
  <script>
    window.onload = function() {
      setTimeout(function() { window.print(); }, 150);
    };
  </script>
</body>
</html>`;
  w.document.open();
  w.document.write(html);
  w.document.close();
}

/**
 * Open the user's default mail client with subject + body pre-filled.
 * Falls back to clipboard-paste flow if the body is too long for mailto.
 * @param {{subject?: string, body: string}} args
 */
export async function emailLetter({ subject = "", body }) {
  if (!body || !body.trim()) {
    toast.error("Nothing to email yet");
    return;
  }
  const encSubject = encodeURIComponent(subject);
  const encBody = encodeURIComponent(body);
  const fullUrl = `mailto:?subject=${encSubject}&body=${encBody}`;

  if (fullUrl.length <= MAILTO_URL_LIMIT) {
    window.location.href = fullUrl;
    return;
  }

  // Too long for a reliable mailto — put the letter on the clipboard,
  // open the mail client with a hint, and tell the user to paste.
  const copied = await copyText(body);
  if (copied) {
    const hintBody = encodeURIComponent(
      "(The letter was copied to your clipboard — paste it here with Ctrl+V.)"
    );
    window.location.href = `mailto:?subject=${encSubject}&body=${hintBody}`;
    toast.success("Letter copied to clipboard — paste it into the email body (Ctrl+V)");
  } else {
    toast.error("Letter is too long to email directly. Copy it manually and paste into your email.");
  }
}
