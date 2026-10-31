# pi-pocket-local-dictation

Streaming voice dictation for [Pi Pocket](https://github.com/TannerMidd/pi-pocket) that runs on your own machine.

Tap the mic next to Send (or press Alt+V). Words appear in the message box while you speak. When you stop, an LLM that you choose fixes the transcript using your conversation as context: misheard terms, punctuation, mixed languages. Nothing leaves your machine unless you point the cleanup step at a cloud API.

- **Local speech-to-text:** [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with any GGML model.
- **Any cleanup LLM:** LM Studio, llama.cpp (`llama-server`), Ollama, or any OpenAI-compatible endpoint.
- **A better model per language:** hear the live words with a fast general model, then re-transcribe with a model tuned for the language you spoke (for example Thonburian Whisper for Thai).
- **The existing mic button:** no new UI. The extension replaces the browser's `SpeechRecognition` with a streaming one, so the mic, Alt+V, caret handling, and drafts all work as before.

## Install

1. Install whisper.cpp, so that `whisper-server` exists:

   ```sh
   brew install whisper-cpp          # macOS; on Linux build whisper.cpp and use its whisper-server
   ```

2. Download a model into `~/.cache/whisper-models` (the extension looks there by default; any other folder works if you set `liveModel` and `finalModels`, for example on an external drive):

   ```sh
   mkdir -p ~/.cache/whisper-models && cd ~/.cache/whisper-models
   curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin   # 574 MB, 99 languages
   ```

   Smaller or older machines: `ggml-base.bin` (148 MB) from the same place.

3. Install the extension. In Pi Pocket: **Menu → Extensions → Discover → local-dictation → Install**. Or by hand, copy `local-dictation.ts` and the `local-dictation/` folder into `~/.pi-pocket/extensions/`.
4. Turn it on in **Menu → Extensions**, then reload the page. Allow the microphone when the browser asks. The browser only gives a page the microphone over https or on localhost, as for Pi Pocket's own dictation.

The first dictation after a quiet half hour takes a few seconds longer while the models load. Your speech is buffered meanwhile, so nothing is lost.

## Cleanup with a local LLM

Open **Menu → Extensions → local-dictation → Settings**. Cleanup is on by default and talks to an OpenAI-compatible server at `cleanupUrl`.

| Server | `cleanupUrl` | Start it |
|---|---|---|
| LM Studio | `http://127.0.0.1:1234/v1` (default) | Load a model, then **Developer → Start Server** |
| llama.cpp | `http://127.0.0.1:8080/v1` | `llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M` |
| Ollama | `http://127.0.0.1:11434/v1` | `ollama run qwen3:4b-instruct` |
| OpenCode Go (DeepSeek) | `https://opencode.ai/inference/go/openai/v1` | `cleanupModel` `deepseek-v4.1-flash`, `cleanupKey` your key, `cleanupHeaders` `x-opencode-session: local-dictation`, `cleanupReasoning` `none` |
| Another cloud API | its `/v1` base URL | set `cleanupKey` and `cleanupModel` |

Set `cleanupModel` to the model's name on that server (LM Studio and llama.cpp accept an empty name and use the loaded model). The call sits between "stop" and the final text, so pick a fast model and no reasoning: set `cleanupReasoning` to `none` when the service supports it (in my tests `low` was about five times slower and no more accurate).

**Small local models can make things worse.** Qwen3-4B-Instruct (Q4_K_M) first translated Thai into English, even though the prompt forbids it; the extension now names the transcript's script in the request and drops any answer whose script mix differs. It still made mistakes on clean Thai speech (6.4% error before cleanup, 8.3% after). A large hosted model (DeepSeek Flash) left it at about 6.4% to 7.0% on the same clips. Cleanup is for what recognition cannot know: your terms, names, and the conversation. Try your own speech, and leave `cleanupUrl` empty if cleanup does not help you.

If the server is off, slow, or answers something that looks like an answer instead of a correction, you get the raw transcript. Leave `cleanupUrl` empty to turn cleanup off.

`cleanupNotes` is added to the instructions. Put your names, projects, and terms there ("Spell Pi Pocket, whisper.cpp, and Kubernetes exactly like this").

## A better model for your language

Whisper large-v3-turbo is fast but weak in some languages. Set `finalModels` to give a language its own model, one per line:

```
thai=/Users/me/.cache/whisper-models/thonburian-large-v3-q5_0.bin
```

While you speak, the live model hears you and says which language it heard. When you stop, if a model is set for that language, it transcribes the whole recording again, and that text goes to the cleanup step. Other languages keep the live model's text. Language names are whisper.cpp's (`thai`, `japanese`, ...) or ISO codes (`th`, `ja`, ...).

Thai example, with Thonburian Whisper (Apache-2.0, by the Biomedical and Data Lab at Mahidol University):

```sh
curl -LO https://huggingface.co/Freitag621/thonburian-whisper-large-v3-ggml/resolve/main/thonburian-large-v3-q5_0.bin   # 1.1 GB
```

It keeps English words that you mix into Thai ("แล้วเพิ่ม test ด้วย") in English, but it garbles English-only sentences, which is why it is a final pass for Thai only.

### How much it helps

Character error rate on real Thai clips from Google's [FLEURS](https://huggingface.co/datasets/google/fleurs) test set (lower is better), whisper.cpp on an Apple M4, `bench/bench.py`:

| Recognition (40 clips) | CER | Time |
|---|---|---|
| large-v3-turbo q5_0 (Thai forced) | 15.9% | 51 s |
| Typhoon Whisper turbo q5_0 (converted from `typhoon-ai/typhoon-whisper-turbo`) | 11.0% | 51 s |
| **Thonburian large-v3 q5_0** | **8.4%** | 114 s |
| Thonburian, beam size 5 | 8.0% | 199 s |
| Thonburian medium q5_0 | 8.8% | 86 s |

The whole extension, streaming each clip as a microphone would (10 clips): **6.4%** with the language-routed Thonburian pass, against about 15% for the live model alone. DeepSeek Flash cleanup without reasoning, and with no conversation context, measured 7.0% on that read-aloud speech, so on clean audio cleanup is neutral. Its value is with context (your terms and names) and with messy, mixed-language speech, which FLEURS does not have. Measure on your own audio: the scripts in `bench/` show how.

## Settings

| Setting | Default | What it does |
|---|---|---|
| `server` | empty | Path to `whisper-server`. Empty: Homebrew's folders, then `PATH`. |
| `liveModel` | empty | GGML file for live words and English. Empty: `ggml-large-v3-turbo-q5_0.bin` or `ggml-base.bin` in `~/.cache/whisper-models`. |
| `finalModels` | empty | `language=path` lines for a second, better pass. |
| `whisperPrompt` | empty | Words Whisper should expect. Keep it short and neutral. A long prompt in one language can make Whisper answer in that language. |
| `threads` | 6 | CPU threads for whisper-server. |
| `idleMinutes` | 30 | The servers stop after this long without dictation. |
| `cleanupUrl` | `http://127.0.0.1:1234/v1` | OpenAI-compatible base URL. Empty: no cleanup. |
| `cleanupModel` | empty | Model name on that server. |
| `cleanupKey` | empty | API key, if the server needs one. Stays on the server. |
| `cleanupHeaders` | empty | Extra request headers, one `Name: value` per line. |
| `cleanupReasoning` | empty | Sent as `reasoning_effort` when set. |
| `cleanupNotes` | empty | Extra instructions: names and terms to spell right. |

## How it works

```
mic -> browser (16 kHz PCM, every ~0.9 s) -> POST /api/x/local-dictation/push
        -> whisper-server (live model): words so far, language heard   -> shown in the box
stop -> final-pass model for that language (all audio)                 -> raw text
        -> cleanup LLM with recent messages + the box's text           -> fixed text replaces the words
```

- Audio goes from your browser to Pi Pocket's server and on to `127.0.0.1` ports only. whisper.cpp servers listen on localhost, one for each model, started when needed and stopped when idle.
- Recordings longer than 20 s are cut at a quiet moment, so the live pass stays fast. A recording stops by itself after 5 minutes.
- The cleanup prompt is told never to translate, and its answer is rejected (the raw text stays) if its scripts differ from the transcript's (a translation), if it adds brackets, or if it is far longer or shorter.
- Language routing for the final pass uses the script of the live text (Thai letters mean Thai), then the language the live pass heard most often. A single short window is easily mistaken for a related language.
- Only the owner turns the extension on and changes settings. Routes are open to people who can steer a session.

## Limits

- Safari and Chrome with a microphone permission over https or localhost. Tested on desktop Chrome; report what you find on Safari and phones.
- The "stop" delay is the final pass plus cleanup, a few seconds for a short message. Your live words stay in the box meanwhile.
- Whisper can make up text from silence or noise. Known phrases are filtered, and quiet audio is skipped, but it is not perfect.
- Needs Pi Pocket 0.22.0 or later (extension settings).

## Development

```sh
node test/smoke.mjs                       # offline: loads the module, checks settings and routes
SETTINGS='{"finalModels":"thai=/path/thonburian.bin","cleanupUrl":""}' \
  node test/e2e.mjs clips/ refs.tsv 10    # audio -> text, scored against references
```

Set `LOCAL_DICTATION_DEBUG=1` to log the time of each stop.

## Credits

[whisper.cpp](https://github.com/ggml-org/whisper.cpp) and OpenAI Whisper (MIT); [Thonburian Whisper](https://github.com/biodatlab/thonburian-whisper) (Apache-2.0); [Typhoon Whisper](https://huggingface.co/typhoon-ai/typhoon-whisper-turbo) (MIT); [FLEURS](https://huggingface.co/datasets/google/fleurs) (CC-BY-4.0).

## Licence

MIT.
