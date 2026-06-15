/**
 * Web Speech API wrappers. Graceful fallback if unsupported.
 */

const LANG_TO_BCP47 = {
  english: "en-IN",
  tamil: "ta-IN",
  hindi: "hi-IN",
};

export function isRecognitionSupported() {
  return "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
}

export function createRecognizer(language) {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = LANG_TO_BCP47[language] || "en-IN";
  r.interimResults = false;
  r.maxAlternatives = 1;
  r.continuous = false;
  return r;
}

let speakingUtterance = null;

export function speak(text, language) {
  if (!("speechSynthesis" in window)) return;
  cancelSpeak();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = LANG_TO_BCP47[language] || "en-IN";
  u.rate = 1;
  u.pitch = 1;
  speakingUtterance = u;
  window.speechSynthesis.speak(u);
}

export function cancelSpeak() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  speakingUtterance = null;
}
