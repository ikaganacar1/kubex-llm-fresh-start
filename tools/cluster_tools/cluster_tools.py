import requests
import logging
from typing import Dict, Any, List

# Logger'ı yapılandırarak olası hataların ve işlemlerin takibini kolaylaştırıyoruz.
logger = logging.getLogger(__name__)

class ClusterAPITools:
    """Kubernetes Cluster API işlemleri için gerçek API çağrılarını yöneten sınıf"""
    
    def __init__(self, base_url: str, active_cluster_id: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.active_cluster_id = active_cluster_id

    def list_clusters(self) -> Dict[str, Any]:
        """Sistemde kayıtlı tüm cluster'ları listeler."""
        try:
            url = f"{self.base_url}/clusters"
            
            print(f"[ClusterAPI] Cluster listesi alınıyor: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()  # HTTP 4xx veya 5xx hatalarında exception fırlatır
            
            clusters = response.json()
            cluster_count = len(clusters)
            
            return {
                "status": "success",
                "cluster_count": cluster_count,
                "clusters": clusters,
                "message": f"Toplam {cluster_count} adet cluster bulundu."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ClusterAPI] Cluster listesi alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Cluster listesi alınamadı: {str(e)}"
            }

    def create_cluster(self, name: str) -> Dict[str, Any]:
        """Sisteme yeni bir cluster kaydı oluşturur."""
        try:
            url = f"{self.base_url}/clusters"
            payload = {"name": name}
            
            print(f"[ClusterAPI] Yeni cluster oluşturuluyor: {name}")
            
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            
            new_cluster_data = response.json()
            
            return {
                "status": "success",
                "created_cluster": new_cluster_data,
                "message": f"'{name}' adıyla yeni bir cluster kaydı başarıyla oluşturuldu."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ClusterAPI] Cluster oluşturulamadı: {e}")
            return {
                "status": "error",
                "message": f"'{name}' cluster'ı oluşturulamadı: {str(e)}",
                "requested_name": name
            }

    def get_cluster_details(self) -> Dict[str, Any]:
        """Aktif cluster'ın yapılandırma detaylarını gösterir."""
        if not self.active_cluster_id:
            return {"status": "error", "message": "İşlem için aktif bir cluster ID'si belirtilmelidir."}
            
        try:
            url = f"{self.base_url}/clusters/{self.active_cluster_id}"
            print(f"[ClusterAPI] Cluster detayı alınıyor: {self.active_cluster_id}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            cluster_details = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "details": cluster_details,
                "message": f"'{self.active_cluster_id}' ID'li cluster'ın detayları alındı."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ClusterAPI] Cluster detayı alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Cluster detayı alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }

    def get_cluster_summary(self) -> Dict[str, Any]:
        """Aktif cluster'ın canlı kaynak özetini alır."""
        if not self.active_cluster_id:
            return {"status": "error", "message": "İşlem için aktif bir cluster ID'si belirtilmelidir."}
            
        try:
            url = f"{self.base_url}/clusters/summary/{self.active_cluster_id}"
            print(f"[ClusterAPI] Cluster özeti alınıyor: {self.active_cluster_id}")
            
            # Bu işlem cluster'a bağlanıp bilgi alacağı için timeout süresi daha uzun olabilir.
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            summary_data = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "summary": summary_data,
                "message": f"'{self.active_cluster_id}' ID'li cluster için kaynak özeti başarıyla alındı."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ClusterAPI] Cluster özeti alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Cluster özeti alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }

    def update_cluster(self, kubeconfigs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aktif cluster'ın bağlantı bilgilerini (kubeconfig) günceller."""
        if not self.active_cluster_id:
            return {"status": "error", "message": "İşlem için aktif bir cluster ID'si belirtilmelidir."}

        try:
            url = f"{self.base_url}/clusters/{self.active_cluster_id}"
            payload = {"kubeconfigs": kubeconfigs}
            
            print(f"[ClusterAPI] Cluster güncelleniyor: {self.active_cluster_id}")
            
            response = self.session.patch(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "api_response": result,
                "message": f"'{self.active_cluster_id}' ID'li cluster başarıyla güncellendi."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ClusterAPI] Cluster güncellenemedi: {e}")
            return {
                "status": "error",
                "message": f"Cluster güncellenemedi: {str(e)}",
                "cluster_id": self.active_cluster_id
            }