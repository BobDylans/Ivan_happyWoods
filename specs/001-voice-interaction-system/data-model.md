# Data Model: Voice-Based AI Agent Interaction System

**Date**: 2025-10-13  
**Feature**: Voice interaction system data structures and relationships

## Core Entities

### ConversationSession

**Purpose**: Represents an active voice interaction session with state management

**Fields**:
- `session_id`: str (UUID) - Unique identifier for the session
- `user_id`: str (optional) - User identifier for authenticated sessions  
- `created_at`: datetime - Session creation timestamp
- `last_activity`: datetime - Last interaction timestamp
- `status`: SessionStatus - ACTIVE, PAUSED, TERMINATED
- `conversation_history`: List[Message] - Ordered list of conversation messages
- `context_summary`: str (optional) - Compressed context for long conversations
- `preferences`: UserPreferences - Voice and interaction preferences

**Relationships**:
- One-to-many with Message entities
- One-to-one with UserPreferences

**Validation Rules**:
- session_id must be valid UUID format
- conversation_history limited to 100 messages (context window management)
- last_activity updated on each user interaction
- session expires after 30 minutes of inactivity

**State Transitions**:
- ACTIVE → PAUSED (user request or temporary disconnect)
- PAUSED → ACTIVE (user reconnection within timeout)
- ACTIVE/PAUSED → TERMINATED (explicit end or timeout)

### Message

**Purpose**: Represents individual messages in conversation flow

**Fields**:
- `message_id`: str (UUID) - Unique message identifier
- `session_id`: str (UUID) - Parent session reference
- `timestamp`: datetime - Message creation time
- `role`: MessageRole - USER, ASSISTANT, SYSTEM, TOOL
- `content_type`: ContentType - TEXT, AUDIO, IMAGE, TOOL_CALL, TOOL_RESULT
- `text_content`: str (optional) - Text representation of message
- `audio_data`: bytes (optional) - Raw audio data for voice messages
- `audio_format`: str (optional) - Audio format specification (wav, mp3, etc.)
- `metadata`: dict - Additional message metadata (confidence scores, processing time, etc.)
- `tool_calls`: List[ToolCall] (optional) - Tool invocations for this message
- `processing_status`: ProcessingStatus - PENDING, PROCESSING, COMPLETED, FAILED

**Relationships**:
- Many-to-one with ConversationSession
- One-to-many with ToolCall entities

**Validation Rules**:
- Either text_content or audio_data must be present
- audio_data requires audio_format when present
- tool_calls only valid for ASSISTANT role messages
- message_id must be unique within session

### UserPreferences

**Purpose**: User-specific configuration for voice and interaction preferences

**Fields**:
- `preferred_voice`: str - TTS voice selection (alloy, echo, fable, onyx, nova, shimmer)
- `speech_rate`: float - TTS speed multiplier (0.5-2.0)
- `language`: str - Primary language code (en-US, en-GB, etc.)
- `interrupt_enabled`: bool - Allow conversation interruption
- `context_length`: int - Preferred conversation context window
- `notification_preferences`: dict - Audio feedback preferences

**Validation Rules**:
- speech_rate between 0.5 and 2.0
- language must be supported language code
- context_length between 5 and 50 messages

### ToolCall

**Purpose**: Represents external tool invocations and their results

**Fields**:
- `call_id`: str (UUID) - Unique tool call identifier
- `tool_name`: str - Name of the invoked tool
- `function_name`: str - Specific function within the tool
- `arguments`: dict - Input arguments for the tool call
- `result`: dict (optional) - Tool execution result
- `status`: ToolStatus - PENDING, EXECUTING, COMPLETED, FAILED, TIMEOUT
- `started_at`: datetime - Tool execution start time
- `completed_at`: datetime (optional) - Tool execution completion time
- `error_message`: str (optional) - Error details if execution failed

**Relationships**:
- Many-to-one with Message
- Many-to-one with ToolRegistry entry

**Validation Rules**:
- tool_name must exist in ToolRegistry
- arguments must match tool function signature
- timeout after 10 seconds for tool execution
- error_message required when status is FAILED

### ToolRegistry

**Purpose**: Catalog of available tools and their capabilities

**Fields**:
- `tool_id`: str - Unique tool identifier
- `tool_name`: str - Human-readable tool name
- `description`: str - Tool capability description
- `category`: ToolCategory - SEARCH, CALCULATION, AI_GENERATION, ANALYSIS, TIME
- `functions`: List[ToolFunction] - Available functions in this tool
- `status`: ToolStatus - AVAILABLE, UNAVAILABLE, MAINTENANCE
- `health_check_url`: str (optional) - Health monitoring endpoint
- `last_health_check`: datetime (optional) - Last successful health check

**Validation Rules**:
- tool_name must be unique across registry
- at least one function must be defined
- health_check_url required for external tools

### ToolFunction

**Purpose**: Specific function definition within a tool

**Fields**:
- `function_name`: str - Function identifier
- `description`: str - Function purpose and usage
- `parameters`: dict - JSON schema for function parameters
- `return_schema`: dict - JSON schema for function return value
- `timeout_seconds`: int - Maximum execution time
- `retry_count`: int - Number of retry attempts on failure

**Validation Rules**:
- function_name unique within tool
- parameters must be valid JSON schema
- timeout_seconds between 1 and 30

## Audio Processing Entities

### AudioStream

**Purpose**: Manages real-time audio data flow and buffering

**Fields**:
- `stream_id`: str (UUID) - Unique stream identifier
- `session_id`: str (UUID) - Associated conversation session
- `direction`: StreamDirection - INPUT, OUTPUT
- `format`: AudioFormat - Sample rate, channels, bit depth
- `buffer`: bytes - Current audio buffer
- `buffer_size`: int - Maximum buffer size in bytes
- `chunk_size`: int - Processing chunk size
- `status`: StreamStatus - STARTED, STREAMING, STOPPED, ERROR

**Validation Rules**:
- buffer_size limited to 1MB for memory management
- chunk_size optimized for low latency (typically 1024-4096 bytes)
- stream automatically stopped after 5 minutes of inactivity

## Configuration Entities

### ServiceConfig

**Purpose**: External service configuration and credentials

**Fields**:
- `service_name`: str - Service identifier (openai, anthropic, etc.)
- `api_key`: str - Service authentication key
- `base_url`: str - Service endpoint URL
- `model_name`: str - Specific model to use
- `timeout_seconds`: int - Request timeout
- `rate_limit`: dict - Rate limiting configuration
- `enabled`: bool - Service availability flag

**Validation Rules**:
- api_key encrypted at rest
- base_url must be valid HTTPS URL
- timeout_seconds between 5 and 60

## Entity Relationships Summary

```
ConversationSession (1) → (many) Message
Message (1) → (many) ToolCall
ToolCall (many) → (1) ToolRegistry
ConversationSession (1) → (1) UserPreferences
ConversationSession (1) → (many) AudioStream
```

## Data Flow Patterns

### Voice Message Processing
1. AudioStream receives voice input
2. STT service converts to Message with text_content
3. LangGraph agent processes message, may create ToolCall entities
4. Tool results stored as new Message with TOOL_RESULT type
5. Agent response generated as Message with ASSISTANT role
6. TTS service converts to audio, stored in AudioStream

### Session Context Management
1. ConversationSession maintains rolling window of Message entities
2. Context summarization when approaching limits
3. Old messages archived, summary retained in context_summary
4. User preferences applied to voice synthesis and interaction flow