# Group Management Features

## Overview

RSS2Pod provides comprehensive group management for organizing RSS feeds into podcast generation pipelines.

## Features

### 1. Group Editing

Access: TUI → Group Management → Press 'e' on selected group

**Editable Fields:**
1. **Name** - Group identifier
2. **Enabled** - Toggle group active/inactive (true/false)
3. **Trigger Type** - Generation trigger:
   - `time` - Cron-based scheduling
   - `count` - Article count threshold
   - `llm` - LLM-based topic evaluation
   - `mixed` - Combination of triggers
4. **Source IDs** - Comma-separated list of Fever API feed IDs

**Usage:**
```bash
# TUI 方式
npm run tui
# Navigate to Group Management
# Press 'e' to edit selected group
# Press 1-4 to select field
# Press 's' to save

# CLI 方式（支持 trigger 配置）
npm run cli -- group:edit <id> -t count --threshold 10
npm run cli -- group:edit <id> -c "0 18 * * *"
npm run cli -- group:edit <id> -t mixed -c "0 9 * * *"
```

### 2. Temporary File Saving

During pipeline execution, all intermediate files are saved to:
```
data/media/{groupId}/episode_{timestamp}/
```

**Saved Files:**
- `segment_001_host.mp3` - TTS audio segments
- `segment_002_guest.mp3`
- `final.mp3` - Concatenated final audio
- `segments.txt` - FFmpeg concatenation list

**Database Storage:**
- LLM inputs/outputs stored in `episodes.script` (JSON format)
- TTS responses logged in pipeline logs

### 3. LLM Prompt Configuration

Prompts can be customized in `config.json`:

```json
{
  "llm": {
    "provider": "dashscope",
    "model": "Qwen/Qwen2.5-72B-Instruct-128K",
    "prompts": {
      "source_summary": "Your custom summary prompt...",
      "script_generation": "Your custom script prompt..."
    }
  }
}
```

**Group-Level Overrides:**
Groups can override default prompts via TUI edit screen (future enhancement).

### 4. Podcast Feed Distribution

**Library:** `podcast` npm library (v2.0.1)

**Feed Generation:**
- Automatic after pipeline completion
- Saves to: `data/media/feeds/{groupId}.xml`
- iTunes-compliant RSS format

**Feed Includes:**
- Episode title and description
- Audio enclosure with proper MIME type
- iTunes metadata (author, category, explicit flag)
- GUID for episode tracking

**Access Feed:**
```
http://localhost:3000/api/feeds/{groupId}.xml
```

### 5. Pipeline Stages

The 7-stage pipeline:
1. **Fetch** - Download articles from Fever API
2. **Source Summary** - Generate per-source summaries (LLM)
3. **Group Aggregate** - Combine source summaries
4. **Script** - Generate podcast script (LLM)
5. **Audio** - Synthesize TTS audio segments
6. **Episode** - Save episode to database
7. **Feed** - Generate podcast RSS feed

## Configuration

All settings in `config.json`:

```json
{
  "database": { "path": "./data/rss2pod.db" },
  "fever": { "baseUrl": "...", "email": "...", "password": "..." },
  "llm": { "provider": "dashscope", "apiKey": "..." },
  "tts": { "provider": "siliconflow", "apiKey": "..." },
  "scheduler": { "checkInterval": 60, "maxConcurrentGroups": 3 },
  "media": { "basePath": "./data/media", "retentionDays": 30 }
}
```

## CLI Commands

```bash
# List groups
npm run cli -- group:list

# Create group
npm run cli -- group:create "My Group" -s "1,2,3" -t time

# Edit group (TUI)
npm run tui

# Run pipeline
npm run cli -- generate:run {groupId}

# View history
npm run cli -- generate:history {groupId}
```
