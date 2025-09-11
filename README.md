# KUBEX Multi-Agent Assistant 🧩

A sophisticated Kubernetes management system built with a multi-agent architecture using Ollama LLMs and Streamlit for the user interface. This assistant provides natural language interaction with Kubernetes clusters through specialized AI agents.

## 🚀 Features

- **Multi-Agent Architecture**: Specialized agents for different Kubernetes operations
- **Natural Language Interface**: Chat with your cluster using plain English
- **Real-time Streaming**: Live responses with thinking process visibility
- **Tool-based Operations**: Structured API interactions with parameter validation
- **Session Management**: Persistent conversation context and cluster state
- **Welcome Screen**: Interactive tool overview for new users

## 🏗️ Architecture

### Core Components

- **Agent Manager**: Central orchestrator managing multiple specialized agents
- **Specialized Agents**: Domain-specific agents for Kubernetes operations
- **LLM Services**: Abstracted language model operations
- **Tool System**: Structured API interactions with validation
- **Streamlit UI**: Modern web interface with chat functionality

### Agent Types

| Agent | Description | Tools |
|-------|-------------|-------|
| 🖥️ **Cluster Agent** | Kubernetes cluster operations | List, create, update clusters |
| 📦 **Namespace Agent** | Namespace management | Create, delete, list namespaces |
| 🚀 **Deployment Agent** | Deployment operations | Deploy, scale, update applications |
| 📚 **Repository Agent** | Helm repository management | Add, list, delete repositories, install charts |

## 📋 Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) server running with supported models
- Kubernetes API server (configurable endpoint)
- Required Python packages (auto-installed)

## 🛠️ Installation & Setup

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kubex-llm-fresh-start
   ```

2. **Run the application**
   ```bash
   python run.py
   ```
   
   This will automatically:
   - Install required dependencies (`streamlit`, `requests`)
   - Launch the Streamlit web interface

3. **Configure connections**
   - Open the sidebar in the web interface
   - Set your Ollama URL (default: `http://ai.ikaganacar.com`)
   - Set your Kubex API URL (default: `http://10.67.67.195:8000`)
   - Choose your model (default: `qwen3:8b`)

### Manual Installation

```bash
# Install dependencies
pip install streamlit requests

# Run the UI directly
streamlit run ui.py
```

## 🎮 Usage

### Getting Started

1. **Connect to Services**: Use the sidebar to configure Ollama and Kubex URLs
2. **Select Cluster**: Choose an active cluster from the dropdown
3. **Explore Tools**: View the welcome screen to see available operations
4. **Start Chatting**: Use natural language to interact with your cluster

### Example Interactions

```
User: "List all deployments"
Assistant: [Routes to Deployment Agent, executes list_deployments tool]

User: "Add prometheus repository"
Assistant: [Routes to Repository Agent, asks for repository details]

User: "Scale my-app to 5 replicas"
Assistant: [Routes to Deployment Agent, executes scale operation]

User: "Create a new namespace called testing"
Assistant: [Routes to Namespace Agent, creates namespace]
```

### Advanced Features

- **Parameter Collection**: Missing parameters are collected through interactive forms
- **Context Awareness**: Agents maintain conversation history for better responses
- **Error Handling**: Comprehensive error reporting with debugging information
- **Session Reset**: Soft and full reset options for clearing state

## 🔧 Configuration

### Environment Variables

The application uses configurable URLs that can be set through the UI:

- `OLLAMA_URL`: Ollama server endpoint
- `KUBEX_URL`: Kubernetes API server endpoint
- `MODEL_NAME`: LLM model to use

### Supported Models

- `qwen3:8b` (default)
- `qwen3:4b`
- `qwen3:1.7b`

## 📁 Project Structure

```
kubex-llm-fresh-start/
├── run.py                  # Main entry point
├── ui.py                   # Streamlit web interface
├── agent_manager.py        # Central agent orchestrator
├── base_agent.py          # Abstract agent base class
├── ollama.py              # Ollama client integration
├── agents/                # Specialized agents
│   ├── cluster_agent.py
│   ├── namespace_agent.py
│   ├── deployment_agent.py
│   └── repository_agent.py
├── llm_services/          # LLM service abstractions
│   ├── router_llm_service.py
│   ├── tool_calling_llm_service.py
│   └── summarizer_llm_service.py
├── tools/                 # Tool implementations
│   ├── cluster_tools/
│   ├── namespace_tools/
│   ├── deployment_tools/
│   └── repository_tools/
└── CLAUDE.md             # Development guidance
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify Ollama server is running
   - Check URL endpoints are accessible
   - Ensure model is downloaded in Ollama

2. **Cluster Selection Issues**
   - Verify Kubex API is responding
   - Check cluster list endpoint
   - Refresh the page to reload cluster data

3. **Tool Execution Errors**
   - Check debug panel for detailed error messages
   - Verify cluster permissions
   - Ensure required parameters are provided

### Debug Mode

Enable debug mode in the sidebar to see:
- Conversation memory
- Agent context details
- Tool execution logs
- Parameter processing information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow the existing agent pattern for new functionality
- Add comprehensive error handling
- Include parameter validation in tools
- Update documentation for new features
- Test with multiple model types

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM hosting
- [Streamlit](https://streamlit.io/) for the web interface framework
- [Kubernetes](https://kubernetes.io/) for container orchestration

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the debug panel output
3. Open an issue with detailed error information
4. Include your configuration and model details

---

**Made with ❤️ for Kubernetes management**