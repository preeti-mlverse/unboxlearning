import { api } from "./api";

/** Speak text aloud: provider TTS when available, otherwise the browser's built-in voice. Resolves when done. */
export class Speaker {
  private audio: HTMLAudioElement | null = null;
  private stopped = false;
  providerOk = true;

  async say(text: string, lang?: string): Promise<void> {
    this.stopped = false;
    const clean = text.replace(/\[e\d+\]/g, "").replace(/[*_`#>]/g, "").slice(0, 3800);
    if (this.providerOk) {
      try {
        const { url } = await api.tts(clean);
        if (this.stopped) return;
        await new Promise<void>((resolve) => {
          this.audio = new Audio(url);
          this.audio.onended = () => resolve();
          this.audio.onerror = () => resolve();
          this.audio.play().catch(() => resolve());
        });
        return;
      } catch {
        this.providerOk = false; // fall through to the browser voice for the rest of the session
      }
    }
    if (this.stopped || !("speechSynthesis" in window)) return;
    await new Promise<void>((resolve) => {
      const u = new SpeechSynthesisUtterance(clean);
      if (lang) u.lang = lang;
      u.rate = 1.02;
      u.onend = () => resolve();
      u.onerror = () => resolve();
      window.speechSynthesis.speak(u);
    });
  }

  stop() {
    this.stopped = true;
    this.audio?.pause();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }
}
