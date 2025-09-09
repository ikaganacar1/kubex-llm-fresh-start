from typing import Dict, Any

class RepositoryToolManager:
    """Repository tool'larını yöneten API tool manager"""
    
    def __init__(self):
        self.tools = self._define_tools()
    
    def _define_tools(self) -> Dict[str, Any]:
        """Repository işlemleri için mevcut tool'ları tanımla"""
        return {
            "list_repositories": {
                "summary": "Cluster'daki tüm Helm repository'lerini listeler",
                "description": "Kubernetes cluster'ına eklenmiş tüm Helm repository'lerinin listesini getirir",
                "method": "GET",
                "path": "/repositories/{cluster_id}/list",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    }
                ]
            },
            
            "add_repository": {
                "summary": "Cluster'a yeni bir Helm repository ekler",
                "description": "Belirtilen URL'deki Helm repository'yi cluster'a ekler",
                "method": "POST",
                "path": "/repositories/{cluster_id}/add",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    },
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Repository'nin adı (örn: prometheus-community)"
                    },
                    {
                        "name": "url",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Repository'nin URL'i (örn: https://prometheus-community.github.io/helm-charts)"
                    }
                ]
            },
            
            "delete_repository": {
                "summary": "Belirtilen Helm repository'yi siler",
                "description": "Cluster'dan belirtilen repository'yi kaldırır",
                "method": "DELETE",
                "path": "/repositories/{cluster_id}/{repository_name}",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    },
                    {
                        "name": "repository_name",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Silinecek repository'nin adı"
                    }
                ]
            },
            
            "update_repositories": {
                "summary": "Tüm Helm repository'lerini günceller",
                "description": "Cluster'daki tüm repository'lerin index'lerini günceller (helm repo update)",
                "method": "POST",
                "path": "/repositories/{cluster_id}/update",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    }
                ]
            },
            
            "install_chart": {
                "summary": "Helm chart'ı cluster'a yükler",
                "description": "Belirtilen Helm chart'ı cluster'a deploy eder",
                "method": "POST",
                "path": "/repositories/{cluster_id}/install",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    },
                    {
                        "name": "chart",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yüklenecek chart (örn: prometheus-community/kube-prometheus-stack)"
                    },
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Release adı (örn: kube-prometheus-stack)"
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Chart'ın yükleneceği namespace"
                    },
                    {
                        "name": "values",
                        "in": "body",
                        "required": False,
                        "type": "object",
                        "description": "Chart için özel values (opsiyonel)"
                    }
                ]
            },
            
            "check_health": {
                "summary": "Helm servisinin sağlık durumunu kontrol eder",
                "description": "Helm servisinin çalışıp çalışmadığını kontrol eder",
                "method": "GET",
                "path": "/repositories/health",
                "parameters": []
            }
        }