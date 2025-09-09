from typing import Dict, Any, Generator
from base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class NamespaceAgent(BaseAgent):
    """Kubernetes Namespace işlemleri için özelleşmiş agent - İyileştirilmiş context yönetimi ile"""
    
    def __init__(self, client):
        super().__init__(
            client=client,
            category="Kubernetes Namespace",
            description="Kubernetes namespace'lerini yönetir, listeler, oluşturur ve siler."
        )
        # Gelecekte NamespaceAPITools ve NamespaceToolManager eklenecek
    
    def get_tools(self) -> Dict[str, Any]:
        """Namespace işlemleri için mevcut araçları döndürür"""
        # Şimdilik örnek araçlar - gerçek implementasyon gelecekte
        return {
            "list_namespaces": {
                "summary": "Tüm namespace'leri listeler",
                "method": "GET",
                "path": "/namespaces",
                "parameters": []
            },
            "create_namespace": {
                "summary": "Yeni bir namespace oluşturur",
                "method": "POST", 
                "path": "/namespaces",
                "parameters": [
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Oluşturulacak namespace'in adı"
                    }
                ]
            },
            "delete_namespace": {
                "summary": "Belirtilen namespace'i siler",
                "method": "DELETE",
                "path": "/namespaces/{namespace_name}",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "path",
                        "required": True,
                        "type": "string", 
                        "description": "Silinecek namespace'in adı"
                    }
                ]
            }
        }
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], original_request: str = None) -> Generator[str, None, None]:
        """Namespace aracını çalıştırır - iyileştirilmiş context ile"""
        logger.info(f"[{self.category}] Araç çalıştırılıyor: '{tool_name}', Parametreler: {parameters}")
        
        # Original request'i güncelle
        if original_request:
            self.last_user_request = original_request
        
        # Şimdilik simüle edilmiş yanıtlar - gerçek API çağrıları gelecekte eklenecek
        if tool_name == "list_namespaces":
            result = {
                "status": "success",
                "namespaces": [
                    {"name": "default", "status": "Active", "age": "30d"},
                    {"name": "kube-system", "status": "Active", "age": "30d"},
                    {"name": "production", "status": "Active", "age": "15d"}
                ]
            }
        elif tool_name == "create_namespace":
            name = parameters.get("name", "unknown")
            result = {
                "status": "success",
                "message": f"Namespace '{name}' başarıyla oluşturuldu",
                "namespace": {"name": name, "status": "Active"}
            }
        elif tool_name == "delete_namespace":
            name = parameters.get("namespace_name", "unknown")
            result = {
                "status": "success", 
                "message": f"Namespace '{name}' başarıyla silindi"
            }
        else:
            result = {"status": "error", "message": f"Bilinmeyen araç: {tool_name}"}
        
        # YENI: Tool result'u context ile birlikte summarize et
        response_generator = self._summarize_result_for_user(result, self.last_user_request)
        
        # Response'u collect et ve context'e ekle
        full_response = ""
        for chunk in response_generator:
            full_response += chunk
            yield chunk
        
        # YENI: Tool execution'ı conversation context'e ekle
        if self.last_user_request:
            self.add_to_conversation_context(self.last_user_request, full_response)