from typing import Dict, Any

class NamespaceToolManager:
    """Namespace tool'larını yönetin API tool manager"""
    
    def __init__(self,active_cluster_id="5546027b-a535-406e-aeb5-7e0588d1f6df"):
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Any]:
        """Namespace işlemleri için mevcut tool'ları tanımla"""
        return {
            "list_namespaces": {
                "summary": "Belirtilen cluster'daki tüm namespace'leri listeler",
                "description": "Kubernetes cluster'ındaki tüm namespace'lerin listesini alır",
                "method": "GET",
                "path": f"/namespaces/{self.active_cluster_id}/instant",
                "parameters": [
                ]
            },
            
            "get_namespace_summary": {
                "summary": "Namespace'lerin pod durumu özet bilgilerini alır",
                "description": "Her namespace için pod sayıları, durumları ve genel istatistikleri gösterir",
                "method": "GET", 
                "path": f"/namespaces/summary/{self.active_cluster_id}",
                "parameters": [
                ]
            },
            
            "show_namespace": {
                "summary": "Belirli bir namespace'in detaylarını gösterir",
                "description": "Belirtilen namespace'in ayrıntılı bilgilerini ve yapılandırmasını alır",
                "method": "GET",
                "path": "/namespaces/show",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "query",
                        "required": True,
                        "type": "string", 
                        "description": "Detayları görüntülenecek namespace'in adı"
                    },
                ]
            }
        }