# Backend Model Configuration

## Current Setup

The system is now configured to use **Qwen/Qwen2.5-Coder-32B-Instruct** for backend code generation.

### Model Configuration

- **Backend Provider**: OpenRouter
- **Backend Model**: `qwen/qwen-2.5-coder-32b-instruct`
- **Max Tokens**: 8192
- **Temperature**: 0.1

### Configuration Location

The LLM configuration is defined in `config/settings.py`:

```python
@dataclass
class LLMConfig:
    backend_provider: str = "openrouter"
    backend_model: str = "qwen/qwen-2.5-coder-32b-instruct"
    backend_max_tokens: int = 8192
    backend_temperature: float = 0.1
    # ... other settings
```

### How It Works

1. **GenerationPipeline** (`generation/pipeline.py`) automatically uses the backend model configuration
2. The **BackendAgent** (`backend_agent.py`) uses this pipeline for all backend code generation
3. All backend components (models, APIs, services, controllers, middleware) are generated using Qwen/Qwen2.5-Coder-32B-Instruct

### Environment Setup

Make sure you have the required API key set:

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Or on Windows PowerShell:

```powershell
$env:OPENROUTER_API_KEY="your-api-key-here"
```

### Customization

To change the model or settings, edit `config/settings.py`:

```python
class LLMConfig:
    backend_model: str = "your/preferred-model"
    backend_max_tokens: int = 8192  # Adjust as needed
    backend_temperature: float = 0.1  # 0.0-1.0 for creativity
```

### Supported Providers

- `openrouter` - Access to multiple models including Qwen
- `openai` - GPT models
- `anthropic` - Claude models
- `huggingface` - Hugging Face models
- `groq` - Fast inference models

### Model Advantages

**Qwen2.5-Coder-32B-Instruct** is optimized for:
- ✅ Code generation and completion
- ✅ Following coding patterns and best practices
- ✅ Multi-language support
- ✅ Large context window (32K+ tokens)
- ✅ High code quality and accuracy
