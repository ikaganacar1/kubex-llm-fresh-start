import requests
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RepositoryAPITools:
    """Kubernetes Helm Repository API işlemleri için gerçek API tool'ları"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def list_repositories(self, cluster_id: str) -> Dict[str, Any]:
        """Belirtilen cluster'daki tüm Helm repository'lerini listeler"""
        try:
            url = f"{self.base_url}/repositories/{cluster_id}/list"
            logger.info(f"[RepositoryAPI] Repository listesi alınıyor: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": cluster_id,
                "repositories": data.get("repositories", []),
                "count": data.get("count", 0),
                "message": f"{data.get('count', 0)} repository bulundu"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository listesi alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Repository listesi alınamadı: {str(e)}",
                "cluster_id": cluster_id
            }
    
    def add_repository(self, cluster_id: str, name: str, url: str) -> Dict[str, Any]:
        """Cluster'a yeni bir Helm repository ekler"""
        try:
            api_url = f"{self.base_url}/repositories/{cluster_id}/add"
            payload = {
                "name": name,
                "url": url
            }
            
            logger.info(f"[RepositoryAPI] Repository ekleniyor: {name} -> {url}")
            
            response = self.session.post(api_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": cluster_id,
                "name": name,
                "url": url,
                "message": data.get("message", "Repository başarıyla eklendi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository eklenemedi: {e}")
            return {
                "status": "error",
                "message": f"Repository eklenemedi: {str(e)}",
                "cluster_id": cluster_id,
                "name": name
            }
    
    def delete_repository(self, cluster_id: str, repository_name: str) -> Dict[str, Any]:
        """Belirtilen Helm repository'yi siler"""
        try:
            url = f"{self.base_url}/repositories/{cluster_id}/{repository_name}"
            
            logger.info(f"[RepositoryAPI] Repository siliniyor: {repository_name}")
            
            response = self.session.delete(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": cluster_id,
                "name": repository_name,
                "message": data.get("message", "Repository başarıyla silindi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository silinemedi: {e}")
            return {
                "status": "error",
                "message": f"Repository silinemedi: {str(e)}",
                "cluster_id": cluster_id,
                "name": repository_name
            }
    
    def update_repositories(self, cluster_id: str) -> Dict[str, Any]:
        """Cluster'daki tüm Helm repository'lerini günceller"""
        try:
            url = f"{self.base_url}/repositories/{cluster_id}/update"
            
            logger.info(f"[RepositoryAPI] Repository'ler güncelleniyor")
            
            response = self.session.post(url, timeout=60)  # Update işlemi uzun sürebilir
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "status": "success",
                "cluster_id": cluster_id,
                "message": data.get("message", "Repository'ler başarıyla güncellendi")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[RepositoryAPI] Repository'ler güncellenemedi: {e}")
            return {
                "status": "error",
                "message": f"Repository'ler güncellenemedi: {str(e)}",
                "cluster_id": cluster_id
            }
    
    def install_chart(self, cluster_id: str, chart: str, name: str, namespace: str, values: Optional[Dict] = None) -> Dict[str, Any]:
        """Helm chart'ı cluster'a yükler"""
        try:
            url = f"{self.base_url}/repositories/{cluster_id}/install"
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
                "cluster_id": cluster_id,
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
                "cluster_id": cluster_id,
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