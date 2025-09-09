from typing import Dict, Any, Generator
from base_agent import BaseAgent
from cluster_tools.tool_manager import ToolManager
from cluster_tools.cluster_tools import ClusterAPITools
import logging

logger = logging.getLogger(__name__)

class ClusterAgent(BaseAgent):
    """Kubernetes Cluster işlemleri için özelleşmiş agent"""
    
    def __init__(self, client):
        super().__init__(
            client=client,
            category="Kubernetes Cluster",
            description="Kubernetes cluster'larını yönetir, listeler, oluşturur ve günceller."
        )
        self.tool_manager = ToolManager()
        self.cluster_api = ClusterAPITools(base_url="http://localhost:8000")
    
    def get_tools(self) -> Dict[str, Any]:
        """Cluster işlemleri için mevcut araçları döndürür"""
        return self.tool_manager.tools
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Generator[str, None, None]:
        """Cluster aracını çalıştırır"""
        logger.info(f"[{self.category}] Araç çalıştırılıyor: '{tool_name}', Parametreler: {parameters}")
        
        tool_function = getattr(self.cluster_api, tool_name, None)
        if not tool_function:
            logger.error(f"[{self.category}] '{tool_name}' aracı için fonksiyon bulunamadı.")
            return self._create_error_response(f"'{tool_name}' adlı aracın çalıştırma metodu bulunamadı.")
        
        try:
            result = tool_function(**parameters)
            return self._summarize_result_for_user(result)
        except Exception as e:
            logger.error(f"[{self.category}] Araç çalıştırılırken hata oluştu ({tool_name}): {e}")
            return self._create_error_response(f"Araç çalıştırılırken hata oluştu: {str(e)}")
