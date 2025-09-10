import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
def _summarize_deployments(deployments: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {}
        for d in deployments:
            namespace = d.get("namespace", "unknown-namespace")
            if namespace not in summary:
                summary[namespace] = []
            
            status_str = f"{d.get('ready_replicas', 0)}/{d.get('replicas', 1)}"
            
            summary[namespace].append({
                "name": d.get("name"),
                "type": d.get("type"),
                "status": status_str,
                "ready": d.get("available", False)
            })
        return summary

class DeploymentAPITools:
    """Kubernetes Deployment API işlemleri için gerçek API tool'ları"""
    
    def __init__(self, base_url: str, active_cluster_id):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.active_cluster_id = active_cluster_id
    
    def list_deployments(self) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/deployments/{self.active_cluster_id}/instant"
            print(f"[DeploymentAPI] Fetching deployment list from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            raw_data = response.json()

            summarized_view = _summarize_deployments(raw_data)
            
            total_count = len(raw_data)
            available_count = sum(1 for d in raw_data if d.get("available", False))
            
            return {
                "status": "success",
                "cluster_id": self.active_cluster_id,
                "total_resources": total_count,
                "ready_resources": available_count,
                "summary": summarized_view,  # Use the summarized data here
                "message": f"Toplam {total_count} kaynak bulundu, {available_count} tanesi hazır durumda."
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment listesi alınamadı: {e}")
            return {
                "status": "error",
                "message": f"Deployment listesi alınamadı: {str(e)}",
                "cluster_id": self.active_cluster_id
            }
    
    def show_deployment(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """Belirli bir deployment'ın detaylarını gösterir"""
        try:
            url = f"{self.base_url}/deployments/show"
            params = {
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id
            }
            
            print(f"[DeploymentAPI] Deployment detayı alınıyor: {deployment_name}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            deployment_detail = response.json()
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "deployment_detail": deployment_detail,
                "message": f"'{deployment_name}' deployment detayları alındı"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment detayı alınamadı: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment detayı alınamadı: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id
            }
    
    def scale_deployment(self, deployment_name: str, namespace: str, replicas: int) -> Dict[str, Any]:
        """Deployment'ı ölçekler (replica sayısını değiştirir)"""
        try:
            url = f"{self.base_url}/deployments/scale"
            payload = {
                "cluster_id": self.active_cluster_id,
                "deployment_name": deployment_name,
                "namespace": namespace,
                "replicas": replicas
            }
            
            print(f"[DeploymentAPI] Deployment ölçeklendiriliyor: {deployment_name} -> {replicas} replicas")
            
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "new_replica_count": replicas,
                "api_response": result,
                "message": f"'{deployment_name}' deployment {replicas} replica'ya ölçeklendirildi"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment ölçeklendirilemedi: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment ölçeklendirilemedi: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "requested_replicas": replicas
            }
    
    def redeploy_deployment(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """Deployment'ı yeniden dağıtır (restart işlemi)"""
        try:
            url = f"{self.base_url}/deployments/redeploy"
            payload = {
                "cluster_id": self.active_cluster_id,
                "deployment_name": deployment_name,
                "namespace": namespace
            }
            
            print(f"[DeploymentAPI] Deployment yeniden dağıtılıyor: {deployment_name}")
            
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "api_response": result,
                "message": f"'{deployment_name}' deployment yeniden dağıtıldı"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment yeniden dağıtılamadı: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment yeniden dağıtılamadı: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id
            }
    
    def get_deployment_config(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """Deployment'ın detaylı yapılandırmasını alır"""
        try:
            url = f"{self.base_url}/deployments/config"
            params = {
                "cluster_id": self.active_cluster_id,
                "deployment_name": deployment_name,
                "namespace": namespace
            }
            
            print(f"[DeploymentAPI] Deployment config alınıyor: {deployment_name}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            config_data = response.json()
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "config": config_data,
                "message": f"'{deployment_name}' deployment yapılandırması alındı"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment config alınamadı: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment yapılandırması alınamadı: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id
            }
    
    def get_deployment_pods(self, namespace_name: str, deployment_name: str = "apisix") -> Dict[str, Any]:
        """Deployment'a ait pod'ları listeler"""
        try:
            url = f"{self.base_url}/deployments/{deployment_name}/pods"
            params = {
                "cluster_id": self.active_cluster_id,
                "namespace_name": namespace_name
            }
            
            print(f"[DeploymentAPI] Deployment pod'ları alınıyor: {deployment_name}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            pods_data = response.json()
            
            # Pod'ları analiz et
            total_pods = len(pods_data)
            online_pods = sum(1 for p in pods_data if p.get("is_online", False))
            running_pods = sum(1 for p in pods_data if p.get("phase") == "Running")
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace_name,
                "cluster_id": self.active_cluster_id,
                "pod_count": total_pods,
                "online_pods": online_pods,
                "running_pods": running_pods,
                "pods": pods_data,
                "message": f"'{deployment_name}' deployment'ında {total_pods} pod bulundu, {running_pods} tanesi çalışıyor"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment pod'ları alınamadı: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment pod'ları alınamadı: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace_name,
                "cluster_id": self.active_cluster_id
            }
    
    def update_deployment_image(self, deployment_name: str, namespace: str, image: str) -> Dict[str, Any]:
        """Deployment'ın container image'ını günceller"""
        try:
            url = f"{self.base_url}/deployments/image"
            payload = {
                "cluster_id": self.active_cluster_id,
                "deployment_name": deployment_name,
                "namespace": namespace,
                "image": image
            }
            
            print(f"[DeploymentAPI] Deployment image güncelleniyor: {deployment_name} -> {image}")
            
            response = self.session.patch(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "status": "success",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "new_image": image,
                "api_response": result,
                "message": f"'{deployment_name}' deployment image'ı '{image}' olarak güncellendi"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeploymentAPI] Deployment image güncellenemedi: {e}")
            return {
                "status": "error",
                "message": f"'{deployment_name}' deployment image güncellenemedi: {str(e)}",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "cluster_id": self.active_cluster_id,
                "requested_image": image
            }