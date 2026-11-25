# boticus

Teach Claude Code agents real skills by having them watch videos.

The setup has three parts:

1. **Eyes: [`watch`](.claude/skills/watch/SKILL.md).** Downloads any video with yt-dlp, extracts one frame per shot, measures pacing, zooms in on the first 10 s, and pulls a transcript. Claude then looks at the frames. (From [claude-watch](https://github.com/taoufik123-collab/claude-watch), MIT.)
2. **Long-form eyes: [`gemini-watch`](.claude/skills/gemini-watch/SKILL.md).** Gemini watches YouTube URLs natively, audio and visuals, without downloading anything. It handles hour-long tutorials cheaply.
3. **Brain: [`learn`](.claude/skills/learn/SKILL.md) plus role agents.** `/learn <role> <url>` turns videos into sourced, actionable rules in `knowledge/<role>/`. Role agents such as [`video-editor`](.claude/agents/video-editor.md) read that knowledge before every task.

## Setup

Requirements: Python 3.10+, `ffmpeg`, `yt-dlp` (`pip install yt-dlp`).

Optional keys:

| Key | What it unlocks | Get it |
|---|---|---|
| `GEMINI_API_KEY` | `gemini-watch` (YouTube natively) | Free at https://aistudio.google.com/apikey |
| `GROQ_API_KEY` or `OPENAI_API_KEY` | Whisper transcripts for videos with no captions (in `watch`) | console.groq.com/keys |

Set them as environment variables (or in a cloud environment's settings). Never commit them.

> **Claude Code on the web:** the default network policy blocks YouTube and TikTok, so `watch` can't download from them. Add `youtube.com`, `www.youtube.com`, `youtu.be`, `*.googlevideo.com` (and `www.tiktok.com` if you want it) to the environment's allowed hosts, or run locally. `gemini-watch` only needs `generativelanguage.googleapis.com`, because Google fetches the video itself.

## Usage

```
/learn video-editor https://youtu.be/<tutorial> focus on pacing and captions for TikTok
```
```
Use the video-editor agent to critique ./clips/draft.mp4 for TikTok
```
```
Use the video-editor agent to cut ./raw/interview.mp4 into a 45 s vertical clip with burned-in captions
```

## Adding a new role

Copy `.claude/agents/video-editor.md` to `.claude/agents/<role>.md` (for example `social-media-manager`), rewrite it for that role, then run `/learn <role> <urls...>`.
