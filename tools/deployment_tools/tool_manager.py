from typing import Dict, Any

class DeploymentToolManager:
    """Deployment tool'larını yönetin API tool manager"""
    
    def __init__(self,active_cluster_id):
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Any]:
        """Deployment işlemleri için mevcut tool'ları tanımla"""
        return {
            "list_deployments": {
                "summary": "Belirtilen cluster'daki tüm deployment'ları listeler",
                "description": "Kubernetes cluster'ındaki tüm deployment'ların listesini ve durumlarını alır",
                "method": "GET",
                "path": f"/deployments/{self.active_cluster_id}/instant",
                "parameters": [
                ]
            },
            
            "show_deployment": {
                "summary": "Belirli bir deployment'ın detaylarını gösterir",
                "description": "Belirtilen deployment'ın ayrıntılı bilgilerini ve durumunu alır",
                "method": "GET",
                "path": "/deployments/show",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Detayları görüntülenecek deployment'ın adı"
                    },
                    {
                        "name": "namespace",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    }
                ]
            },
            
            "scale_deployment": {
                "summary": "Deployment'ı ölçekler (replica sayısını değiştirir)",
                "description": "Belirtilen deployment'ın pod sayısını (replica) artırır veya azaltır",
                "method": "POST",
                "path": "/deployments/scale",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Ölçeklendirilecek deployment'ın adı"
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    },
                    {
                        "name": "replicas",
                        "in": "body",
                        "required": True,
                        "type": "integer",
                        "description": "Hedef replica sayısı (örn: 3, 5, 10)"
                    }
                ]
            },
            
            "redeploy_deployment": {
                "summary": "Deployment'ı yeniden dağıtır (restart işlemi)",
                "description": "Belirtilen deployment'ı yeniden başlatır, tüm pod'lar yenilenir",
                "method": "POST",
                "path": "/deployments/redeploy",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yeniden dağıtılacak deployment'ın adı"
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    }
                ]
            },
            
            "get_deployment_config": {
                "summary": "Deployment'ın detaylı yapılandırmasını alır",
                "description": "Deployment'ın tam yapılandırma bilgilerini, environment variable'ları ve ayarları gösterir",
                "method": "GET",
                "path": "/deployments/config",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Config'i alınacak deployment'ın adı"
                    },
                    {
                        "name": "namespace",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    }
                ]
            },
            
            "get_deployment_pods": {
                "summary": "Deployment'a ait pod'ları listeler",
                "description": "Belirtilen deployment'ın tüm pod'larını, durumlarını ve IP adreslerini gösterir",
                "method": "GET",
                "path": "/deployments/{deployment_name}/pods",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    },
                    {
                        "name": "deployment_name",
                        "in": "path",
                        "required": False,
                        "type": "string",
                        "description": "Pod'ları alınacak deployment'ın adı (varsayılan: apisix)"
                    }
                ]
            },
            
            "update_deployment_image": {
                "summary": "Deployment'ın container image'ını günceller",
                "description": "Belirtilen deployment'ın Docker image'ını yeni bir versiyona günceller",
                "method": "PATCH",
                "path": "/deployments/image",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Image'ı güncellenecek deployment'ın adı"
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace adı"
                    },
                    {
                        "name": "image",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yeni Docker image adı ve tag'i (örn: harbor.bulut.ai/liman/app:v1.2)"
                    }
                ]
            }
        }