import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class NamespaceAPITools:
    """Kubernetes Namespace API işlemleri için gerçek API tool'ları"""
    
    def __init__(self, base_url: str,active_cluster_id):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.active_cluster_id = active_cluster_id
        
    def list_namespaces(self) -> Dict[str, Any]:
        """Belirtilen cluster'daki tüm namespace'leri listeler"""
        try:
            url = f"{self.base_url}/namespaces/{self.active_cluster_id}/instant"
            print(f"[NamespaceAPI] Namespace listesi alınıyor: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            namespaces = response.json()
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "namespace_count": len(namespaces),
                "namespaces": namespaces,
                "message": f"{len(namespaces)} namespace bulundu"
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[NamespaceAPI] Namespace listesi alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Namespace listesi alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }
    
    def get_namespace_summary(self) -> Dict[str, Any]:
        """Namespace'lerin pod durumu özet bilgilerini alır"""
        try:
            url = f"{self.base_url}/namespaces/summary/{self.active_cluster_id}"
            print(f"[NamespaceAPI] Namespace özet bilgisi alınıyor: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            summary_data = response.json()
            
            # Özet istatistikler hesapla
            total_namespaces = len(summary_data)
            total_pods = sum(ns.get("total_pod_count", 0) for ns in summary_data)
            running_pods = sum(ns.get("running_pod_count", 0) for ns in summary_data)
            failed_pods = sum(ns.get("failed_pod_count", 0) for ns in summary_data)
            pending_pods = sum(ns.get("pending_pod_count", 0) for ns in summary_data)
            
            # En aktif namespace'leri bul
            active_namespaces = sorted(
                summary_data, 
                key=lambda x: x.get("running_pod_count", 0), 
                reverse=True
            )[:5]
            
            # Sorunlu namespace'leri bul
            problematic_namespaces = [
                ns for ns in summary_data 
                if ns.get("failed_pod_count", 0) > 0 or ns.get("pending_pod_count", 0) > 0
            ]
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "summary": {
                    "total_namespaces": total_namespaces,
                    "total_pods": total_pods,
                    "running_pods": running_pods,
                    "failed_pods": failed_pods,
                    "pending_pods": pending_pods
                },
                "top_active_namespaces": active_namespaces,
                "problematic_namespaces": problematic_namespaces,
                "all_namespaces": summary_data,
                "message": f"Cluster'da {total_namespaces} namespace, {total_pods} pod bulundu"
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[NamespaceAPI] Namespace özet bilgisi alınamadı: {e}")
            return {
                "status": "error", 
                "message": f"Namespace özet bilgisi alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }
    
    def show_namespace(self, namespace_name: str) -> Dict[str, Any]:
        """Belirli bir namespace'in detaylarını gösterir"""
        try:
            url = f"{self.base_url}/namespaces/show"
            params = {
                "namespace_name": namespace_name,
                "cluster_id": self.active_cluster_id
            }
            
            print(f"[NamespaceAPI] Namespace detayı alınıyor: {namespace_name}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            namespace_detail = response.json()
            
            return {
                "status": "success",
                "namespace_name": namespace_name,
                "cluster_id": self.active_cluster_id,
                "namespace_detail": namespace_detail,
                "message": f"'{namespace_name}' namespace detayları alındı"
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[NamespaceAPI] Namespace detayı alınamadı: {e}")
            return {
                "status": "error",
                "message": f"'{namespace_name}' namespace detayı alınamadı: {str(e)}",
                "namespace_name": namespace_name,
                "cluster_id": self.active_cluster_id
            }