# llm_services/router_llm_service.py

import json
from typing import Dict, Any,Optional

class RouterLLMService:
    """
    Kullanıcı talebini analiz ederek en uygun agent'ı seçmekle sorumlu LLM servisi.
    """
    def __init__(self, client: Any):
        self.client = client
        self.system_prompt = ""

    def _build_system_prompt(self, agents: Dict[str, Any], context_summary: str) -> str:
        """Router LLM için sistem komutunu dinamik olarak oluşturur."""
        agent_descriptions = [
            f"- {key}: {agent.category} - {agent.description}" 
            for key, agent in agents.items()
        ]
        agents_text = "\n".join(agent_descriptions)

        context_info = f"\n\n### SON SOHBET OZETI ###\n{context_summary}\n" if context_summary else ""

        return (
            "### GÖREV VE KİMLİK ###\n"
            "Sen, KUBEX Kubernetes Yönetim Platformu'nun ana yönlendiricisi olan bir \"Triage Uzmanı\"sın. "
            "Temel görevin, kullanıcıdan gelen talebi derinlemesine analiz ederek, bu talebi en doğru şekilde karşılayacak "
            "uzmanlık alanını (agent) belirlemektir.\n\n"
            f"### UZMANLIK ALANLARI (AGENT'LAR) ###\n{agents_text}\n"
            f"{context_info}"
            "### KARAR VERME SÜRECİ ###\n"
            "1. **Amacı Anlama:** Kullanıcının talebini incele (listeleme, oluşturma, silme, genel sohbet vb.).\n"
            "2. **Kaynak Türü:** Talebin merkezindeki kaynağı belirle (Cluster, Deployment, Namespace vb.).\n"
            "3. **Bağlamı Değerlendirme:** Sohbet geçmişini kullanarak kullanıcının bir önceki adıma devam edip etmediğini anla.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Kararını ve mantığını (`reasoning`) içeren, **SADECE** aşağıdaki formatta bir JSON objesi döndür. "
            "Yanıtına başka hiçbir metin ekleme.\n\n"
            "```json\n"
            "{\n"
            '  "agent": "ilgili_agent_adi | chat",\n'
            '  "reasoning": "Kararın arkasındaki kısa mantık.",\n'
            '  "response": "Eğer agent \'chat\' ise, kullanıcıya verilecek sohbet cevabı."\n'
            "}\n"
            "```"
        )

    def get_routing_decision(self, user_prompt: str, agents: Dict[str, Any], context_summary: str) -> Dict[str, Any]:
        """LLM'den agent yönlendirme kararını alır."""
        system_prompt = self._build_system_prompt(agents, context_summary)
        try:
            response = self.client.chat(
                user_prompt=user_prompt, 
                system_prompt=system_prompt, 
                use_history=False  # Router için history kullanma
            )
            content = response.get("message", {}).get("content", "{}")
            
            print(f"[RouterLLMService] Raw LLM Output: {content}")
            
            # Geliştirilmiş JSON çıkarma
            json_result = self._extract_json_safely(content)
            if json_result:
                return json_result
            else:
                raise ValueError("Geçerli JSON bulunamadı")
                
        except Exception as e:
            print(f"[RouterLLMService] LLM'den geçerli yanıt alınamadı: {e}")
            print(f"[RouterLLMService] Raw content: {content if 'content' in locals() else 'N/A'}")
            return {
                "agent": "chat", 
                "reasoning": "Routing sırasında bir hata oluştu.",
                "response": "İsteğinizi anlayamadım, lütfen daha açık bir şekilde ifade eder misiniz?"
            }
    
    def _extract_json_safely(self, content: str) -> Optional[Dict[str, Any]]:
        """İçerikten JSON objesini güvenli şekilde çıkarır"""
        import json
        import re
        
        # Method 1: Standard JSON regex patterns
        json_patterns = [
            r'\{[^{}]*"agent"[^{}]*\}',     # Single line with agent key
            r'\{.*?"agent".*?\}',           # Multi-line with agent key  
            r'\{.*\}',                      # Any JSON object
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                json_str = match.group(0)
                try:
                    decoded_json = json.loads(json_str)
                    if "agent" in decoded_json:
                        return decoded_json
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Manual key extraction
        agent_match = re.search(r'"agent"\s*:\s*"([^"]+)"', content)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', content)
        response_match = re.search(r'"response"\s*:\s*"([^"]+)"', content)
        
        if agent_match:
            result = {"agent": agent_match.group(1)}
            if reasoning_match:
                result["reasoning"] = reasoning_match.group(1)
            if response_match:
                result["response"] = response_match.group(1)
            return result
        
        return None