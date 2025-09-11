import requests
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RepositoryAPITools:
    """Kubernetes Helm Repository API işlemleri için gerçek API tool'ları"""
    
    def __init__(self, base_url: str, active_cluster_id):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.active_cluster_id = active_cluster_id
        
    def list_repositories(self) -> Dict[str, Any]:
        """Belirtilen cluster'daki tüm Helm repository'lerini listeler"""
        try:
            url = f"{self.base_url}/repositories/{self.active_cluster_id}/list"
            logger.info(f"[RepositoryAPI] Repository listesi alınıyor: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "repositories": data.get("repositories", []),
                "count": data.get("count", 0),
                "message": f"{data.get('count', 0)} repository bulundu"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository listesi alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Repository listesi alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }
    
    def add_repository(self, **kwargs) -> Dict[str, Any]:
        """Cluster'a yeni bir Helm repository ekler"""
        try:
            # Extract required parameters
            name = kwargs.get('name')
            url = kwargs.get('url')
            
            # Validate required parameters
            if not name:
                return {
                    "status": "error",
                    "message": "Repository adı (name) gerekli",
                    "cluster_id": self.active_cluster_id
                }
            
            if not url:
                return {
                    "status": "error", 
                    "message": "Repository URL'si (url) gerekli",
                    "cluster_id": self.active_cluster_id
                }
            
            api_url = f"{self.base_url}/repositories/{self.active_cluster_id}/add"
            payload = {
                "name": name,
                "url": url
            }
            
            logger.info(f"[RepositoryAPI] Repository ekleniyor: {name} -> {url}")
            logger.info(f"[RepositoryAPI] API URL: {api_url}")
            logger.info(f"[RepositoryAPI] Payload: {payload}")
            
            response = self.session.post(api_url, json=payload, timeout=30)
            logger.info(f"[RepositoryAPI] Response status: {response.status_code}")
            
            response.raise_for_status()
            
            # Check if response has content before trying to parse JSON
            if response.content:
                try:
                    data = response.json()
                except ValueError as e:
                    logger.warning(f"[RepositoryAPI] Invalid JSON response: {e}")
                    data = {"message": "Repository başarıyla eklendi"}
            else:
                data = {"message": "Repository başarıyla eklendi"}
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "name": name,
                "url": url,
                "message": data.get("message", "Repository başarıyla eklendi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository eklenemedi: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', str(e))
                except:
                    error_detail = str(e)
            else:
                error_detail = str(e)
            return {
                "status": "error",
                "message": f"Repository eklenemedi: {error_detail}",
                "cluster_id": self.active_cluster_id,
                "name": name,
                "url": url
            }
    
    def delete_repository(self, **kwargs) -> Dict[str, Any]:
        """Belirtilen Helm repository'yi siler"""
        try:
            # Extract required parameter
            repository_name = kwargs.get('repository_name')
            
            # Validate required parameter
            if not repository_name:
                return {
                    "status": "error",
                    "message": "Repository adı (repository_name) gerekli",
                    "cluster_id": self.active_cluster_id
                }
            
            url = f"{self.base_url}/repositories/{self.active_cluster_id}/{repository_name}"
            
            logger.info(f"[RepositoryAPI] Repository siliniyor: {repository_name}")
            
            response = self.session.delete(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "name": repository_name,
                "message": data.get("message", "Repository başarıyla silindi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository silinemedi: {e}")
            return {
                "status": "error",
                "message": f"Repository silinemedi: {str(e)}",
                "cluster_id": self.active_cluster_id,
                "name": repository_name
            }
    
    def update_repositories(self) -> Dict[str, Any]:
        """Cluster'daki tüm Helm repository'lerini günceller"""
        try:
            url = f"{self.base_url}/repositories/{self.active_cluster_id}/update"
            
            logger.info(f"[RepositoryAPI] Repository'ler güncelleniyor")
            
            response = self.session.post(url, timeout=60)  # Update işlemi uzun sürebilir
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "message": data.get("message", "Repository'ler başarıyla güncellendi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository'ler güncellenemedi: {e}")
            return {
                "status": "error",
                "message": f"Repository'ler güncellenemedi: {str(e)}",
                "cluster_id": self.active_cluster_id
            }
    
    def install_chart(self, **kwargs) -> Dict[str, Any]:
        """Helm chart'ı cluster'a yükler"""
        try:
            # Extract required parameters
            chart = kwargs.get('chart')
            name = kwargs.get('name')
            namespace = kwargs.get('namespace')
            values = kwargs.get('values')
            
            # Validate required parameters
            if not chart:
                return {
                    "status": "error",
                    "message": "Chart adı (chart) gerekli",
                    "cluster_id": self.active_cluster_id
                }
            
            if not name:
                return {
                    "status": "error",
                    "message": "Release adı (name) gerekli",
                    "cluster_id": self.active_cluster_id
                }
                
            if not namespace:
                return {
                    "status": "error",
                    "message": "Namespace adı (namespace) gerekli",
                    "cluster_id": self.active_cluster_id
                }
            
            url = f"{self.base_url}/repositories/{self.active_cluster_id}/install"
            payload = {
                "chart": chart,
                "name": name,
                "namespace": namespace
            }
            
            # Eğer values parametresi varsa ekle
            if values:
                payload["values"] = values
            
            logger.info(f"[RepositoryAPI] Chart yükleniyor: {chart} -> {namespace}/{name}")
            
            response = self.session.post(url, json=payload, timeout=120)  # Install işlemi uzun sürebilir
            response.raise_for_status()
            
            # Response boş olabilir, kontrol et
            if response.content:
                data = response.json()
                message = data.get("message", f"Chart '{chart}' başarıyla yüklendi")
            else:
                message = f"Chart '{chart}' başarıyla yüklendi"
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "chart": chart,
                "release_name": name,
                "namespace": namespace,
                "message": message
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Chart yüklenemedi: {e}")
            return {
                "status": "error",
                "message": f"Chart yüklenemedi: {str(e)}",
                "cluster_id": self.active_cluster_id,
                "chart": chart
            }
    
    def check_health(self) -> Dict[str, Any]:
        """Helm servisinin sağlık durumunu kontrol eder"""
        try:
            url = f"{self.base_url}/repositories/health"
            
            logger.info(f"[RepositoryAPI] Helm health check yapılıyor")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            return {
                "status": "success",
                "message": "Helm servisi sağlıklı",
                "healthy": True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Helm health check başarısız: {e}")
            return {
                "status": "error",
                "message": f"Helm servisi yanıt vermiyor: {str(e)}",
                "healthy": False
            }