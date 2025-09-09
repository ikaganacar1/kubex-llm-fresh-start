# agent.py - Backward compatibility için
# Bu dosya eski KubernetesAgent sınıfını AgentManager'a yönlendirir

from agent_manager import AgentManager
from ollama import OllamaClient

class KubernetesAgent:
    """Geriye uyumluluk için wrapper sınıf"""
    
    def __init__(self, client: OllamaClient):
        # Eski interface'i yeni AgentManager'a yönlendir
        self.agent_manager = AgentManager(client)
        self.client = client
    
    @property
    def waiting_for_parameters(self):
        """Eski property'i yeni yapıya yönlendir"""
        status = self.agent_manager.get_current_status()
        return status["waiting_for_parameters"]
    
    @property 
    def current_tool_context(self):
        """Eski property'i yeni yapıya yönlendir"""
        status = self.agent_manager.get_current_status()
        return status["tool_context"]
    
    def process_request(self, prompt: str):
        """Eski metodu yeni yapıya yönlendir"""
        return self.agent_manager.route_request(prompt)
    
    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict):
        """Eski metodu yeni yapıya yönlendir"""
        return self.agent_manager.finalize_request(tool_name, extracted_params, collected_params)
    
    def reset_context(self):
        """Eski metodu yeni yapıya yönlendir"""
        self.agent_manager.reset_all_contexts()
